import time
from fastapi import FastAPI, Request
from pydantic import BaseModel
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

# Force CPU
device = torch.device("cpu")

# Load model & tokenizer once at startup
base_model = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
adapter_path = "./tinyllama-finetuned"

print("🔧 Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(base_model)

print("🔧 Loading base model...")
model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.float32).to(device)

print("🔧 Merging LoRA...")
model = PeftModel.from_pretrained(model, adapter_path).to(device)
model = model.merge_and_unload()
model.eval()
print("✅ Model ready.")

# FastAPI app
app = FastAPI()

# Request body
class ChatRequest(BaseModel):
    user_input: str

@app.post("/chat")
def chat(req: ChatRequest):
    t0 = time.time()
    
    chat = [{"role": "user", "content": req.user_input}]
    input_text = tokenizer.apply_chat_template(chat, tokenize=False)

    t1 = time.time()
    inputs = tokenizer(input_text, return_tensors="pt").to(device)
    
    t2 = time.time()
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=50,
            do_sample=True,
            top_k=50,
            top_p=0.9,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id,
        )
    
    t3 = time.time()
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    t4 = time.time()

    return {
        "response": response,
        "timing": {
            "tokenization": round(t2 - t1, 2),
            "inference": round(t3 - t2, 2),
            "decoding": round(t4 - t3, 2),
            "total": round(t4 - t0, 2)
        }
    }
