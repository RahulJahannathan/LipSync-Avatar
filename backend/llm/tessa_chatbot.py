# llm/tessa_chatbot.py

import os
import sys
import time
import logging
from contextlib import contextmanager
from llama_cpp import Llama

logger = logging.getLogger(__name__)

@contextmanager
def suppress_stdout():
    with open(os.devnull, 'w') as devnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = devnull, devnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

class TessaChatbot:
    def __init__(self, model_path="llm/tinyllama.gguf"):
        logger.info("🧠 Initializing Tessa LLM model...")

        start_time = time.time()

        with suppress_stdout():
            self.llm = Llama(
                model_path=model_path,
                n_threads=1,        # 🔽 Reduce threads to lower CPU usage (adjustable)
                n_batch=8,          # 🔄 Small batch size for faster single-turn inference
                n_ctx=256,          # 🔽 Reduce context window for small, casual chats
                f16_kv=True,        # ✅ Use float16 for kv cache (faster, less memory)
                verbose=False,
                logits_all=False,   # 🔕 Disable logits unless needed
                use_mlock=False     # 🚫 Avoid locking RAM
            )

        self.system_prompt = (
            "You are Tessa, a friendly and casual chatbot. "
            "Reply only to greetings or small talk like 'hi', 'how are you'. "
            "Don't answer knowledge-based or technical questions. "
            "Stay cheerful, short, and casual.\n"
        )

        logger.info(f"✅ Tessa model initialized in {time.time() - start_time:.2f}s")

    def get_response(self, user_input: str) -> str:
        prompt = f"{self.system_prompt}### Instruction: {user_input}\n### Response:"
        logger.info(f"💬 Prompting LLM...")

        start = time.time()
        output = self.llm(
            prompt=prompt,
            max_tokens=64,             # 🔽 Limit token output for fast, short replies
            stop=["### Instruction:"]
        )
        logger.info(f"✅ Response in {time.time() - start:.2f}s")

        return output["choices"][0]["text"].strip()


# 🔁 Only loaded once when FastAPI starts
tessa = TessaChatbot()
