import sys
import wave
import numpy as np
from fastrtc import get_tts_model
from loguru import logger

tts_model = get_tts_model(model_path="./models/tts")

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

def text_to_audio(text: str):
    logger.debug(f"📘 Input Text: {text}")
    for audio_chunk in tts_model.stream_tts_sync(text):
        yield audio_chunk
    logger.debug("🎶 Audio streaming completed.")

def text_to_speech(text, filename="output.wav"):
    sample_rate = 16000  # Default if not provided by chunk
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit audio
        wf.setframerate(sample_rate)

        for chunk in text_to_audio(text):
            if isinstance(chunk, tuple) and len(chunk) == 2:
                rate, audio_array = chunk
                sample_rate = rate  # Update sample rate from model
                wf.setframerate(sample_rate)

                # Convert float32 [-1.0, 1.0] to int16 [-32768, 32767]
                audio_array = np.clip(audio_array, -1.0, 1.0)
                audio_int16 = (audio_array * 32767).astype(np.int16)
                wf.writeframes(audio_int16.tobytes())
            else:
                logger.warning(f"Unexpected audio chunk format: {type(chunk)} - {chunk}")

text_to_speech("Hello, this is a test of the text-to-speech functionality.")
