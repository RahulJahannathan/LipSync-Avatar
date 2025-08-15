# main_ws.py
# FastAPI + WebSocket, token streaming from llama.cpp, chunked TTS + Rhubarb lipsync
# -------------------------------------------------------
# pip install fastapi uvicorn websockets pyttsx3
# pip install "llama-cpp-python>=0.2.80"
# On Windows also: pip install pywin32
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
import traceback
import audioop
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from llama_cpp import Llama
import pyttsx3
import io
import wave
TTS_GUARD = asyncio.Semaphore(1)
# ---------- Config ----------
AUDIO_DIR = Path("audios"); AUDIO_DIR.mkdir(exist_ok=True)
BIN_DIR = Path("bin"); BIN_DIR.mkdir(exist_ok=True)

LLM_PATH = "./llm/tinyllama.gguf"  # your GGUF path
N_THREADS = os.cpu_count() or 4
CTX_LEN = 1024
N_BATCH = 256

# streaming & TTS chunking knobs
CHUNK_MAX_TOKENS = 12            # flush to TTS after this many tokens (fallback)
CHUNK_PUNCTUATION = r"[.!?]\s$"  # regex used to detect sentence-end flush
TTS_RATE = 135                   # pyttsx3 voice speed
ASSISTANT_NAME = "tessa"         # choose voice based on this
SYSTEM_PROMPT = (
    "You are Tessa, a friendly casual chatbot. "
    "Only small talk (hi/hello/how are you). Keep replies short. "
    "If asked complex things, say you only chat casually.\n"
)

DEBUG_TTS = os.getenv("DEBUG_TTS", "0") == "1"

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("ws")

# ---------- Helpers ----------
def exec_command(cmd: List[str]) -> str:
    """
    Run a command (list form) and return STDOUT. Raises RuntimeError with stderr on failure.
    Using list form avoids shell quoting issues on Windows.
    """
    log.debug("Running command: %s", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    stdout = (res.stdout or "").strip()
    stderr = (res.stderr or "").strip()
    if res.returncode != 0:
        raise RuntimeError(f"Command {cmd[0]} failed (code={res.returncode}). stderr: {stderr!r} stdout: {stdout!r}")
    return stdout

def b64(bytes_data: bytes) -> str:
    return base64.b64encode(bytes_data).decode("utf-8")

def to_pcm16_mono(wav_bytes: bytes, target_rate: int = 22050) -> bytes:
    """
    Convert arbitrary WAV bytes to PCM16 mono WAV at target_rate using audioop.
    Returns new WAV bytes.
    """
    with io.BytesIO(wav_bytes) as bio_in:
        try:
            with wave.open(bio_in, "rb") as r:
                n_channels = r.getnchannels()
                sampwidth = r.getsampwidth()
                framerate = r.getframerate()
                n_frames = r.getnframes()
                frames = r.readframes(n_frames)
        except wave.Error as e:
            raise RuntimeError(f"Invalid WAV data: {e}")

    # convert sample width to 2 bytes (16-bit) if needed
    if sampwidth != 2:
        frames = audioop.lin2lin(frames, sampwidth, 2)
        sampwidth = 2

    # downmix to mono if needed
    if n_channels == 2:
        frames = audioop.tomono(frames, 2, 0.5, 0.5)
        n_channels = 1
    elif n_channels != 1:
        # generic collapse of N channels -> average
        width = 2
        samples = len(frames) // (n_channels * width)
        mono = bytearray()
        for i in range(samples):
            acc = 0
            for c in range(n_channels):
                off = (i * n_channels + c) * width
                acc += int.from_bytes(frames[off:off+width], "little", signed=True)
            acc = int(acc / n_channels)
            mono += int(acc).to_bytes(2, "little", signed=True)
        frames = bytes(mono)
        n_channels = 1

    # resample if needed
    if framerate != target_rate:
        frames, _ = audioop.ratecv(frames, 2, 1, framerate, target_rate, None)
        framerate = target_rate

    # re-wrap as WAV
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(framerate)
        w.writeframes(frames)
    return out.getvalue()

""" def wav_bytes_from_pyttsx3(text: str, speaker_name: str) -> bytes:
    if not text.strip():
        return b""

    # 
    # Generate WAV bytes using pyttsx3 (blocking).
    # This function is intended to be called from asyncio.to_thread so it runs in a worker thread.
    # On Windows we initialize COM in this thread.
    # 
    # Import pythoncom lazily (pywin32) because it's windows-only
    if os.name == "nt":
        try:
            import pythoncom
        except Exception as e:
            raise RuntimeError("pythoncom (pywin32) is required on Windows for pyttsx3 in threads. Install with `pip install pywin32`.") from e
        pythoncom.CoInitialize()

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", TTS_RATE)

        # choose voice heuristically
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
                raw = f.read()

            if not raw:
                raise RuntimeError("pyttsx3 produced an empty WAV file")

            # normalize to PCM16 mono 22050 Hz for Rhubarb
            try:
                norm = to_pcm16_mono(raw, target_rate=22050)
            except Exception as e:
                # include raw size in error to help debugging
                raise RuntimeError(f"Failed to normalize WAV (size={len(raw)}): {e}") from e

            return norm
        finally:
            # remove temp file unless debug mode
            try:
                if DEBUG_TTS:
                    log.info("DEBUG_TTS=1 -> keeping tmp wav: %s", tmp_path)
                else:
                    os.remove(tmp_path)
            except Exception:
                pass
    finally:
        if os.name == "nt":
            pythoncom.CoUninitialize() """
import simpleaudio as sa  # pip install simpleaudio
engine = pyttsx3.init()
def wav_bytes_from_pyttsx3(text: str, speaker_name: str) -> bytes:
    """
    Windows: use SAPI directly to create a clean PCM16 mono 22k WAV (best for Rhubarb)
    Non-Windows: fall back to pyttsx3 (unchanged behavior)
    """
    if not text or not text.strip():
        return b""

    if os.name == "nt":
        # --- SAPI path ---
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import comtypes.client as cc
            from comtypes.gen import SpeechLib  # created automatically by comtypes
        except Exception as e:
            # Fall back to pyttsx3 if SAPI/pywin32 isn’t available for some reason
            logging.error("SAPI init failed, falling back to pyttsx3: %s", e)
            return _wav_bytes_from_pyttsx3_portable(text, speaker_name)

        try:
            # Output stream to WAV file
            stream = cc.CreateObject("SAPI.SpFileStream")
            fmt = cc.CreateObject("SAPI.SpAudioFormat")
            fmt.Type = SpeechLib.SAFT22kHz16BitMono  # exactly what Rhubarb prefers
            stream.Format = fmt

            spvoice = cc.CreateObject("SAPI.SpVoice")
            engine.stop()
            # Pick a voice heuristically (optional)
            target_is_female = speaker_name.lower() in {"tessa", "female", "alice"}
            try:
                tokens = spvoice.GetVoices()
                for i in range(tokens.Count):
                    t = tokens.Item(i)
                    desc = t.GetDescription() or ""
                    dlow = desc.lower()
                    if target_is_female and any(k in dlow for k in ["zira", "female", "hazel"]):
                        spvoice.Voice = t
                        break
                    if not target_is_female and any(k in dlow for k in ["david", "male"]):
                        spvoice.Voice = t
                        break
            except Exception:
                pass  # keep default if selection fails

            tmp_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
            # SSFMCreateForWrite = 3
            stream.Open(tmp_path, SpeechLib.SSFMCreateForWrite, True)
            spvoice.AudioOutputStream = stream
            spvoice.Rate = 0  # adjust if you want

            # Speak synchronously into the file
            spvoice.Speak(text)
            spvoice.WaitUntilDone(60_000)
            stream.Close()

            with open(tmp_path, "rb") as f:
                data = f.read()

            if not is_valid_wav(data):
                raise RuntimeError("SAPI produced invalid/empty WAV")

            try:
                if os.getenv("DEBUG_TTS") == "1":
                    logging.info("DEBUG_TTS=1 -> keeping tmp wav: %s", tmp_path)
                else:
                    os.remove(tmp_path)
            except Exception:
                pass

            return data
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass

    # --- Non-Windows fallback: your original pyttsx3 flow (portable) ---
    return _wav_bytes_from_pyttsx3_portable(text, speaker_name)


def _wav_bytes_from_pyttsx3_portable(text: str, speaker_name: str) -> bytes:
    """Your original pyttsx3 path, kept as a fallback for non-Windows."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", TTS_RATE)

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

    tmp_path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    try:
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            raw = f.read()
        if not is_valid_wav(raw):
            raise RuntimeError("pyttsx3 produced invalid/empty WAV")
        return raw
    finally:
        try:
            if os.getenv("DEBUG_TTS") == "1":
                logging.info("DEBUG_TTS=1 -> keeping tmp wav: %s", tmp_path)
            else:
                os.remove(tmp_path)
        except Exception:
            pass


def rhubarb_from_wav_bytes(wav_bytes: bytes) -> Dict[str, Any]:
    """
    Run Rhubarb on WAV bytes and return viseme JSON.
    Uses BIN_DIR/rhubarb.exe (Windows) or BIN_DIR/rhubarb (Unix) by default.
    """
    exe = BIN_DIR / ("rhubarb.exe" if os.name == "nt" else "rhubarb")
    print(exe)
    if not exe.exists():
        # also try PATH fallback
        exe_path = shutil.which("rhubarb")
        if exe_path:
            exe = Path(exe_path)
        else:
            raise FileNotFoundError(f"Rhubarb executable not found at {BIN_DIR} and not on PATH. Put rhubarb (or rhubarb.exe) in {BIN_DIR} or install it and ensure it's on PATH.")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as w:
        w.write(wav_bytes)
        wav_path = w.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as j:
        json_path = j.name

    try:
        cmd = [str(exe), "-f", "json", "-o", json_path, wav_path, "-r", "phonetic"]
        log.info("Running rhubarb: %s", " ".join(cmd))
        try:
            out = exec_command(cmd)
            if out:
                log.debug("rhubarb stdout: %s", out)
        except Exception as e:
            # include stdout/stderr in message from exec_command
            log.error("Rhubarb execution failed: %s", e)
            raise

        # verify json exists and is non-empty
        if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
            # if rhubarb produced no JSON, try to read stdout/stderr by running with shell for extra info
            try:
                debug_cmd = " ".join(cmd)
                res = subprocess.run(debug_cmd, shell=True, capture_output=True, text=True)
                log.error("Rhubarb debug run returned code=%s stdout=%r stderr=%r", res.returncode, res.stdout, res.stderr)
            except Exception:
                log.exception("Failed to run rhubarb debug command")
            raise RuntimeError("Rhubarb produced no JSON output (empty file)")

        with open(json_path, "r", encoding="utf-8") as f:
            txt = f.read()
        if not txt.strip():
            raise RuntimeError("Rhubarb JSON file is empty")
        return json.loads(txt)
    finally:
        # cleanup unless debug
        if DEBUG_TTS:
            log.info("DEBUG_TTS=1 -> kept %s and %s", wav_path, json_path)
        else:
            for p in (wav_path, json_path):
                try:
                    os.remove(p)
                except Exception:
                    pass
def is_valid_wav(wav_bytes: bytes) -> bool:
    if not wav_bytes or len(wav_bytes) < 44:  # smaller than WAV header
        return False
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            wf.getparams()
        return True
    except wave.Error:
        return False

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
                                if not chunk_text.strip():
                                    print(f"[WARN] Skipping TTS for '{who}' — empty string")
                                    return  # Skip this TTS task entirely
                                async with TTS_GUARD:
                                    wav_bytes = await asyncio.to_thread(wav_bytes_from_pyttsx3, chunk_text, who)
                                if not is_valid_wav(wav_bytes):
                                    log.error(f"Invalid WAV in tts_task for '{who}', skipping.")
                                    return                    

                                # ✅ Validate WAV before Rhubarb
                                if not wav_bytes or len(wav_bytes) < 44:
                                    logging.error("Skipping Rhubarb: invalid or empty WAV data")
                                    return  # skip this chunk instead of crashing

                                log.info("TTS wav bytes size: %d", len(wav_bytes))
                                lips = await asyncio.to_thread(rhubarb_from_wav_bytes, wav_bytes)
                                await ws.send_json({
                                    "type": "tts_chunk",
                                    "text": chunk_text,
                                    "audio_b64": b64(wav_bytes),
                                    "lipsync": lips,
                                })
                            except Exception as e:
                                log.error("TTS/Rhubarb error:\n%s", traceback.format_exc())

                        asyncio.create_task(tts_task())

                # flush any residue at the very end
                if buf_text:
                    text_chunk = "".join(buf_text)
                    async def final_tts_task(chunk_text=text_chunk, who=speaker_name):
                        try:
                            async with TTS_GUARD:
                                wav_bytes = await asyncio.to_thread(wav_bytes_from_pyttsx3, chunk_text, who)
                            if not wav_bytes or len(wav_bytes) < 44 or not is_valid_wav(wav_bytes):
                                log.error("Generated TTS WAV is invalid or empty, skipping Rhubarb.")
                                return
                            log.info("Final TTS wav bytes size: %d", len(wav_bytes))
                            lips = await asyncio.to_thread(rhubarb_from_wav_bytes, wav_bytes)
                            await ws.send_json({
                                "type": "tts_chunk",
                                "text": chunk_text,
                                "audio_b64": b64(wav_bytes),
                                "lipsync": lips,
                            })
                        except Exception as e:
                            log.error("Final TTS/Rhubarb error:\n%s", traceback.format_exc())
                    asyncio.create_task(final_tts_task())

                final_text = "".join(full_text).strip()
                # update history
                sess["history"].append({"role": "user", "content": user_text})
                sess["history"].append({"role": "assistant", "content": final_text})

                await ws.send_json({"type": "done", "text": final_text})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("WS error:\n%s", traceback.format_exc())
        try:
            await ws.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass

# optional run
# if __name__ == "__main__":
#     import uvicorn, shutil
    # uvicorn.run("main-ws:app", host="0.0.0.0", port=3000, reload=False)
