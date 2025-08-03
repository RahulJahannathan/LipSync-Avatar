import sys
import wave
from fastrtc import get_stt_model
from loguru import logger

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")

# Load your speech-to-text model
stt_model = get_stt_model(model_path="./models/stt")

def load_audio(file_path):
    """Reads mono 16-bit PCM WAV file and returns raw audio bytes."""
    with wave.open(file_path, 'rb') as wf:
        assert wf.getnchannels() == 1, "Audio must be mono"
        assert wf.getsampwidth() == 2, "Audio must be 16-bit"
        assert wf.getframerate() == 16000, "Audio must be 16kHz"
        audio_data = wf.readframes(wf.getnframes())
    return audio_data

def speech_to_text(file_path):
    audio = load_audio(file_path)
    transcript = stt_model.stt(audio)
    logger.debug(f"📝 Transcript: {transcript}")
    return transcript

# Example usage
text = speech_to_text("output.wav")
print("Transcript:", text)
