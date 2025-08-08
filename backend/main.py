import base64
import json
import os
import subprocess
import time
import wave
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from vosk import Model, KaldiRecognizer
import pyttsx3
from llm.tessa_chatbot import TessaChatbot

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- Directory Setup ---
AUDIO_DIR = Path("audios"); AUDIO_DIR.mkdir(exist_ok=True)
BIN_DIR = Path("bin"); BIN_DIR.mkdir(exist_ok=True)

# --- FastAPI Setup ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

<<<<<<< HEAD
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STT (Vosk Setup) ---
VOSK_MODEL_DIR = "vosk-model-small-en-us-0.15"  # use your downloaded path
OLLAMA_MODEL = "phi:2.7b"

vosk_model = Model(VOSK_MODEL_DIR)
@app.on_event("startup")
def preload_ollama_model():
    # Try waiting a few seconds in case Ollama is still starting up
    for i in range(3):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": "Preloading model for warm start.",
                    "stream": False
                },
                timeout=30
            )
            print("✅ Ollama model preloaded.")
            return
        except requests.exceptions.ConnectionError:
            print(f"🔁 Ollama not ready yet, retrying in 2s... ({i+1}/3)")
            time.sleep(2)
        except Exception as e:
            print(f"⚠️ Unexpected error while preloading Ollama: {e}")
            return
    print("❌ Failed to connect to Ollama after retries.")
=======
# --- Vosk STT Setup ---
VOSK_MODEL_DIR = "vosk-model-small-en-us-0.15"
vosk_model = Model(VOSK_MODEL_DIR)

# --- Input Schema ---
>>>>>>> d4ca12f943ba9b1228df065531f53802261f84f6
class MessageInput(BaseModel):
    message: str

class ChatRequest(BaseModel):
    message: str

# --- Utility Functions ---
def exec_command(command: str):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {result.stderr}")
    return result.stdout

def audio_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_lipsync(wav_path: Path, json_path: Path):
    exec_command(f'"{BIN_DIR / ("rhubarb.exe" if os.name == "nt" else "rhubarb")}" -f json -o "{json_path}" "{wav_path}" -r phonetic')

<<<<<<< HEAD
def generate_audio_espeak(text: str, output_path: Path):
    espeak_dir = Path(__file__).parent / "eSpeak"
    exe_path = espeak_dir / "espeak.exe"
    espeak_data_path = espeak_dir / "espeak-data"

    env = os.environ.copy()
    env["ESPEAK_DATA_PATH"] = str(espeak_data_path.resolve())

    abs_output_path = output_path.resolve()

    # Use female voice f3 and slow speed (130 wpm)
    command = f'"{exe_path}" -v en+f3 -s 140 -w "{abs_output_path}" "{text}"'

    result = subprocess.run(
        command,
        shell=True,
        env=env,
        capture_output=True,
        text=True,
        cwd=str(espeak_dir)
    )

    if result.returncode != 0:
        raise RuntimeError(f"espeak failed: {result.stderr}")
def generate_audio_pyttsx3(text: str, output_path: Path):
    engine = pyttsx3.init()

    # Set slower rate for natural speech
    engine.setProperty("rate", 150)

    # Set female voice if available
    voices = engine.getProperty("voices")
    female_keywords = ["zira", "hazel", "female"]

    for voice in voices:
        if any(keyword in voice.name.lower() or keyword in voice.id.lower() for keyword in female_keywords):
=======
def generate_audio_pyttsx3(text: str, output_path: Path):
    engine = pyttsx3.init()
    engine.setProperty("rate", 135)
    for voice in engine.getProperty("voices"):
        if any(k in voice.name.lower() or k in voice.id.lower() for k in ["zira", "hazel", "female"]):
>>>>>>> d4ca12f943ba9b1228df065531f53802261f84f6
            engine.setProperty("voice", voice.id)
            break
    engine.save_to_file(text, str(output_path.resolve()))
    engine.runAndWait()

# --- LLM Chat Setup ---
class ChatService:
    def __init__(self, chatbot: TessaChatbot):
        self.chatbot = chatbot

    def chat(self, message: str) -> str:
        return self.chatbot.get_response(message)

global_app = app

@app.on_event("startup")
def startup_event():
    tessa = TessaChatbot()
    global_app.state.chat_service = ChatService(tessa)

def get_llm_response(user_message: str) -> str:
<<<<<<< HEAD
    logger.info(f"🔍 Calling LLM for user input: {user_message}")

    system_prompt = """
    You are Tessa, a highly intelligent and emotionally aware virtual avatar created by Algorithmic Avengers.
    You respond directly and concisely to the user's message.
    Keep responses under 2 lines, without filler or self-talk.
    Maintain a professional, friendly tone. Fix grammar silently. Avoid hallucination.
    Answer must be related to the question asked .and the answer should be short and sweet.
    """

    try:
        response = ollama.chat(
            model="phi:2.7b",
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_message.strip()}
            ],
            options={"temperature": 0.5, "num_predict": 150}
        )
        llm_text = response['message']['content'].strip()
        logger.info(f"✅ LLM Response: {llm_text}")
        return llm_text
=======
    try:
        return global_app.state.chat_service.chat(user_message).strip()
>>>>>>> d4ca12f943ba9b1228df065531f53802261f84f6
    except Exception as e:
        logger.error(f"❌ LLM Error: {e}")
        return "[LLM Error]"

# --- Chat API ---
@app.post("/chat")
async def chat(input: MessageInput):
    logger.info("📥 /chat request")
    wav_path, json_path = AUDIO_DIR / "message.wav", AUDIO_DIR / "message.json"

    t0 = time.time()
    llm_text = get_llm_response(input.message)
    logger.info(llm_text)
    t1 = time.time(); logger.info(f"🧠 LLM: {t1 - t0:.2f}s")

    generate_audio_pyttsx3(llm_text, wav_path)
    t2 = time.time(); logger.info(f"🔊 Audio: {t2 - t1:.2f}s")

    generate_lipsync(wav_path, json_path)
    t3 = time.time(); logger.info(f"🗣️ Lipsync: {t3 - t2:.2f}s")

    logger.info(f"✅ Total time: {t3 - t0:.2f}s")
    return {
        "messages": [{
            "text": llm_text,
            "audio": audio_to_base64(wav_path),
            "lipsync": read_json(json_path),
            "facialExpression": "default",
            "animation": "Talking_0"
        }]
    }

# --- Voice API ---
@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    logger.info("📥 /voice request")
    webm_path = AUDIO_DIR / "input.webm"
    wav_input_path, wav_output_path, json_path = AUDIO_DIR / "input.wav", AUDIO_DIR / "output.wav", AUDIO_DIR / "output.json"

    t0 = time.time()
    with open(webm_path, "wb") as f: f.write(await file.read())
    exec_command(f'ffmpeg -y -i "{webm_path}" -ar 16000 -ac 1 "{wav_input_path}"')
    wf = wave.open(str(wav_input_path), "rb")
    rec = KaldiRecognizer(vosk_model, wf.getframerate())
    while True:
        data = wf.readframes(4000)
        if not data: break
        rec.AcceptWaveform(data)
    transcribed = json.loads(rec.FinalResult()).get("text", "").strip()
    t1 = time.time(); logger.info(f"📝 Transcribe: {t1 - t0:.2f}s")

    llm_text = get_llm_response(transcribed)
    t2 = time.time(); logger.info(f"🧠 LLM: {t2 - t1:.2f}s")

    generate_audio_pyttsx3(llm_text, wav_output_path)
    t3 = time.time(); logger.info(f"🔊 Audio: {t3 - t2:.2f}s")

    generate_lipsync(wav_output_path, json_path)
    t4 = time.time(); logger.info(f"🗣️ Lipsync: {t4 - t3:.2f}s")

    logger.info(f"✅ Total time: {t4 - t0:.2f}s")
    return {
        "messages": [{
            "text": llm_text,
            "audio": audio_to_base64(wav_output_path),
            "lipsync": read_json(json_path),
            "facialExpression": "default",
            "animation": "Talking_0"
        }]
    }

@app.get("/")
async def root():
    return {"status": "✅ Optimized FastAPI with Vosk + Tessa is running"}
