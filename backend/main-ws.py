# main_ws.py
# FastAPI + WebSocket, token streaming from llama.cpp, chunked TTS + Rhubarb lipsync
# -------------------------------------------------------
# pip install fastapi uvicorn websockets pyttsx3 vosk
# pip install "llama-cpp-python>=0.2.80"  # prebuilt wheel recommended
# Ensure rhubarb (rhubarb.exe on Windows) is in ./bin or on PATH
# -------------------------------------------------------

import os
import re
import io
import json
import base64
import time
import wave
import asyncio
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from llama_cpp import Llama
import pyttsx3

# ---------- Config ----------
AUDIO_DIR = Path("audios"); AUDIO_DIR.mkdir(exist_ok=True)
BIN_DIR = Path("bin"); BIN_DIR.mkdir(exist_ok=True)

LLM_PATH = "./llm/tinyllama.gguf"  # your GGUF path
N_THREADS = os.cpu_count() or 4
CTX_LEN = 1024
N_BATCH = 256

# streaming & TTS chunking knobs
CHUNK_MAX_TOKENS = 12          # flush to TTS after this many tokens (fallback)
CHUNK_PUNCTUATION = r"[.!?]\s$"  # or when punctuation ends a sentence
TTS_RATE = 135                 # pyttsx3 voice speed
ASSISTANT_NAME = "tessa"       # choose voice based on this
SYSTEM_PROMPT = (
    "You are Tessa, a friendly casual chatbot. "
    "Only small talk (hi/hello/how are you). Keep replies short. "
    "If asked complex things, say you only chat casually.\n"
)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ws")

# ---------- Helpers ----------
def exec_command(command: str) -> str:
    res = subprocess.run(command, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {res.stderr}")
    return res.stdout

def b64(bytes_data: bytes) -> str:
    return base64.b64encode(bytes_data).decode("utf-8")

def wav_bytes_from_pyttsx3(text: str, speaker_name: str) -> bytes:
    """Generate WAV bytes using pyttsx3 (blocking). Run via asyncio.to_thread."""
    engine = pyttsx3.init()
    engine.setProperty("rate", TTS_RATE)

    # pick a voice based on name (very heuristic)
    target_is_female = speaker_name.lower() in {"tessa", "female", "alice"}
    for voice in engine.getProperty("voices"):
        vname = (voice.name or "").lower()
        vid = (voice.id or "").lower()
        if target_is_female and any(k in vname or k in vid for k in ["zira", "female", "hazel"]):
            engine.setProperty("voice", voice.id)
            break
        if not target_is_female and any(k in vname or k in vid for k in ["david", "male"]):
            engine.setProperty("voice", voice.id)
            break

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            data = f.read()
        return data
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

def rhubarb_from_wav_bytes(wav_bytes: bytes) -> Dict[str, Any]:
    """Run Rhubarb on WAV bytes and return viseme JSON. Run via asyncio.to_thread."""
    # write temp wav
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as w:
        w.write(wav_bytes)
        wav_path = w.name
    # run rhubarb
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as j:
        json_path = j.name
    try:
        exe = BIN_DIR / ("rhubarb.exe" if os.name == "nt" else "rhubarb")
        cmd = f'"{exe}" -f json -o "{json_path}" "{wav_path}" -r phonetic'
        exec_command(cmd)
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        for p in (wav_path, json_path):
            try:
                os.remove(p)
            except Exception:
                pass

def build_prompt(history: List[Dict[str,str]], user_text: str) -> str:
    # ultra-short context for latency; last 2 user/assistant pairs
    lines = [SYSTEM_PROMPT.strip()]
    for turn in history[-2:]:
        if turn["role"] == "user":
            lines.append(f"### Instruction: {turn['content']}\n### Response: {turn.get('reply','')}".strip())
        else:
            lines.append(f"### Assistant: {turn['content']}".strip())
    lines.append(f"### Instruction: {user_text}\n### Response:")
    return "\n".join(lines)

# ---------- App ----------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True
)

# load LLM once
log.info("Loading LLM…")
t0 = time.time()
LLM = Llama(
    model_path=LLM_PATH,
    n_ctx=CTX_LEN,
    n_threads=N_THREADS,
    n_batch=N_BATCH,
    verbose=False,
)
log.info("LLM ready in %.2fs", time.time() - t0)

SESSIONS: Dict[str, Dict[str, Any]] = {}  # session_id -> {"history":[{role,content}], "cancel":Event}

@app.get("/")
async def root():
    return {"status": "✅ WS server running"}

@app.websocket("/ws/chat")
async def chat_ws(ws: WebSocket):
    await ws.accept()
    session_id: Optional[str] = None
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "hello":
                session_id = msg.get("session_id") or "default"
                if session_id not in SESSIONS:
                    SESSIONS[session_id] = {"history": [], "cancel": asyncio.Event()}
                else:
                    SESSIONS[session_id]["cancel"].clear()
                await ws.send_json({"type": "hello_ack", "session_id": session_id})
                continue

            if mtype == "cancel":
                if session_id and session_id in SESSIONS:
                    SESSIONS[session_id]["cancel"].set()
                    await ws.send_json({"type": "cancel_ack"})
                continue

            if mtype == "user_text":
                user_text: str = (msg.get("message") or "").strip()
                speaker_name: str = (msg.get("name") or ASSISTANT_NAME).strip() or ASSISTANT_NAME
                if not user_text:
                    await ws.send_json({"type": "error", "error": "empty_text"})
                    continue

                sess = SESSIONS.setdefault(session_id or "default", {"history": [], "cancel": asyncio.Event()})
                sess["cancel"].clear()
                await ws.send_json({"type": "started"})

                prompt = build_prompt(sess["history"], user_text)

                # streaming loop
                buf_tokens: List[str] = []
                buf_text: List[str] = []
                full_text: List[str] = []

                last_flush_time = time.time()

                def should_flush(chunk_so_far: str, tokens_in_chunk: int) -> bool:
                    # flush if punctuation at end or max tokens or 500ms passed (for responsiveness)
                    if tokens_in_chunk >= CHUNK_MAX_TOKENS:
                        return True
                    if re.search(CHUNK_PUNCTUATION, chunk_so_far):
                        return True
                    if time.time() - last_flush_time > 0.5 and len(chunk_so_far) > 6:
                        return True
                    return False

                # run llama.cpp streaming (blocking generator) in executor
                loop = asyncio.get_running_loop()
                q: asyncio.Queue = asyncio.Queue()

                def llm_worker():
                    try:
                        for part in LLM(
                            prompt=prompt,
                            max_tokens=192,
                            temperature=0.7,
                            top_p=0.9,
                            stop=["### Instruction:"],
                            stream=True,
                        ):
                            if sess["cancel"].is_set():
                                break
                            tok = part["choices"][0]["text"]
                            asyncio.run_coroutine_threadsafe(q.put(tok), loop)
                    finally:
                        asyncio.run_coroutine_threadsafe(q.put("__LLM_DONE__"), loop)

                loop.run_in_executor(None, llm_worker)

                # consumer: send tokens immediately; flush TTS chunks opportunistically
                while True:
                    tok = await q.get()
                    if tok == "__LLM_DONE__":
                        break

                    # stream raw token to client UI ASAP
                    await ws.send_json({"type": "token", "text": tok})

                    buf_tokens.append(tok)
                    buf_text.append(tok)
                    full_text.append(tok)

                    chunk = "".join(buf_text)
                    if should_flush(chunk, len(buf_tokens)):
                        # snapshot current chunk
                        text_chunk = chunk
                        buf_tokens.clear()
                        buf_text.clear()
                        last_flush_time = time.time()

                        # run TTS + rhubarb in background, stream when ready
                        async def tts_task(chunk_text=text_chunk, who=speaker_name):
                            try:
                                wav_bytes = await asyncio.to_thread(wav_bytes_from_pyttsx3, chunk_text, who)
                                lips = await asyncio.to_thread(rhubarb_from_wav_bytes, wav_bytes)
                                await ws.send_json({
                                    "type": "tts_chunk",
                                    "text": chunk_text,
                                    "audio_b64": b64(wav_bytes),
                                    "lipsync": lips,
                                })
                            except Exception as e:
                                log.error("TTS/Rhubarb error: %s", e)

                        asyncio.create_task(tts_task())

                # flush any residue at the very end
                if buf_text:
                    text_chunk = "".join(buf_text)
                    async def final_tts_task(chunk_text=text_chunk, who=speaker_name):
                        try:
                            wav_bytes = await asyncio.to_thread(wav_bytes_from_pyttsx3, chunk_text, who)
                            lips = await asyncio.to_thread(rhubarb_from_wav_bytes, wav_bytes)
                            await ws.send_json({
                                "type": "tts_chunk",
                                "text": chunk_text,
                                "audio_b64": b64(wav_bytes),
                                "lipsync": lips,
                            })
                        except Exception as e:
                            log.error("Final TTS/Rhubarb error: %s", e)
                    asyncio.create_task(final_tts_task())

                final_text = "".join(full_text).strip()
                # update history
                sess["history"].append({"role": "user", "content": user_text})
                sess["history"].append({"role": "assistant", "content": final_text})

                await ws.send_json({"type": "done", "text": final_text})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.exception("WS error: %s", e)
        try:
            await ws.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
