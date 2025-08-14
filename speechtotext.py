import sounddevice as sd
import numpy as np
import queue
import time
from faster_whisper import WhisperModel

# ---- Model setup (tune these) ----
MODEL_NAME = "small.en"  # try: "base.en" (faster) or "small.en" (better)
DEVICE = "cpu"           # "cuda" if you have a GPU
COMPUTE_TYPE = "float32"  # "float16" on GPU, "float32" for max accuracy on CPU
model = WhisperModel(MODEL_NAME, device=DEVICE, compute_type=COMPUTE_TYPE)

# ---- Audio / VAD settings ----
SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01     # energy gate for chunking (your existing gate)
SILENCE_DURATION = 0.5       # end-of-utterance silence (seconds)

def speech_to_text(hotwords=None):
    """
    Records speech until ~SILENCE_DURATION of silence, then transcribes.
    Returns (text, response_time_seconds).
    You can pass hotwords like ['Ram'] to bias the decoder.
    """
    audio_queue = queue.Queue()
    current_audio = []
    last_speech_time = time.time()

    def audio_callback(indata, frames, time_info, status):
        if status:
            print(status)
        audio_queue.put(indata.copy())

    def is_speech(audio):
        return np.mean(np.abs(audio)) > SILENCE_THRESHOLD

    # Build a light bias prompt (helps proper nouns)
    initial_prompt = None
    if hotwords:
        # Add a small natural sentence—works better than a raw list
        initial_prompt = "Names that may appear: " + ", ".join(hotwords) + "."

    print("🎤 Speak into the mic... (Ctrl+C to stop)")
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=audio_callback):
        try:
            while True:
                chunk = audio_queue.get().flatten()

                if is_speech(chunk):
                    current_audio.extend(chunk)
                    last_speech_time = time.time()
                else:
                    # End-of-utterance check
                    if current_audio and (time.time() - last_speech_time) > SILENCE_DURATION:
                        audio_np = np.array(current_audio, dtype=np.float32)

                        # Optional: simple normalization can help
                        peak = np.max(np.abs(audio_np)) or 1.0
                        audio_np = audio_np / peak

                        # ---- Transcribe with accuracy-oriented settings ----
                        start_time = time.time()
                        segments, info = model.transcribe(
                            audio_np,
                            language="en",
                            task="transcribe",
                            # Decoding: more accurate than greedy
                            temperature=0.0,     # enables beam search path
                            beam_size=8,         # try 5–10
                            best_of=5,
                            # VAD to ignore non-speech
                            vad_filter=True,
                            vad_parameters={"min_silence_duration_ms": int(SILENCE_DURATION * 1000)},
                            # Reduce cross-utterance bleed for short phrases
                            condition_on_previous_text=False,
                            # Bias for your key terms
                            initial_prompt=initial_prompt,
                        )
                        end_time = time.time()

                        text = " ".join(seg.text.strip() for seg in segments).strip()
                        return text, (end_time - start_time)
        except KeyboardInterrupt:
            return "", 0.0

# Example:
if __name__ == "__main__":
    text, rt = speech_to_text(hotwords=["Ram"])
    print(f"You said: {text}")
    print(f"⏱ Response time: {rt:.3f} s")
