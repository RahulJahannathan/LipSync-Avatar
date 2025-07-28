import base64
import json
import os
import subprocess
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from vosk import Model, KaldiRecognizer
import pyttsx3
import wave
import requests
import ollama

# --- Directory Setup ---
AUDIO_DIR = Path("audios")
BIN_DIR = Path("bin")
AUDIO_DIR.mkdir(exist_ok=True)
BIN_DIR.mkdir(exist_ok=True)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI()

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
class MessageInput(BaseModel):
    message: str

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
    rhubarb_path = BIN_DIR / ("rhubarb.exe" if os.name == "nt" else "rhubarb")
    exec_command(f'"{rhubarb_path}" -f json -o "{json_path}" "{wav_path}" -r phonetic')

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
            engine.setProperty("voice", voice.id)
            break

    # Save to file
    engine.save_to_file(text, str(output_path.resolve()))
    engine.runAndWait()

def get_llm_response(user_message: str) -> str:
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
    except Exception as e:
        logger.error(f"❌ LLM Error: {e}")
        return f"[LLM Error] {str(e)}"

@app.post("/chat")
async def chat(input: MessageInput):
    logger.info("📥 Received /chat request")
    wav_path = AUDIO_DIR / "message.wav"
    json_path = AUDIO_DIR / "message.json"

    llm_text = get_llm_response(input.message)

    logger.info("🎤 Generating audio using pyttsx3")
    generate_audio_pyttsx3(llm_text, wav_path)

    logger.info("🗣️ Generating lipsync with Rhubarb")
    generate_lipsync(wav_path, json_path)

    logger.info("✅ Returning response for /chat")
    return {
        "messages": [{
            "text": llm_text,
            "audio": audio_to_base64(wav_path),
            "lipsync": read_json(json_path),
            "facialExpression": "default",
            "animation": "Talking_0"
        }]
    }


@app.post("/voice")
async def voice(file: UploadFile = File(...)):
    logger.info("📥 Received /voice request")
    webm_path = AUDIO_DIR / "input.webm"
    wav_input_path = AUDIO_DIR / "input.wav"
    wav_output_path = AUDIO_DIR / "output.wav"
    json_path = AUDIO_DIR / "output.json"

    with open(webm_path, "wb") as f:
        f.write(await file.read())
    logger.info("🎧 Uploaded voice file saved")

    exec_command(f'ffmpeg -y -i "{webm_path}" -ar 16000 -ac 1 "{wav_input_path}"')
    logger.info("🔄 Converted voice to 16kHz mono wav")

    wf = wave.open(str(wav_input_path), "rb")
    rec = KaldiRecognizer(vosk_model, wf.getframerate())

    result = ""
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            pass

    transcribed_text = json.loads(rec.FinalResult()).get("text", "").strip()
    logger.info(f"📝 Transcribed text: {transcribed_text}")

    llm_text = get_llm_response(transcribed_text)

    logger.info("🎤 Generating response audio")
    generate_audio_pyttsx3(llm_text, wav_output_path)

    logger.info("🗣️ Generating lipsync with Rhubarb")
    generate_lipsync(wav_output_path, json_path)

    logger.info("✅ Returning response for /voice")
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
    return {"status": "✅ Edge-Optimized FastAPI with Vosk + eSpeak is running"}
