from transformers import AutoModelForCausalLM
from peft import PeftModel
import torch

base_model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
lora_path = "./tinyllama-finetuned"
save_path = "./merged-tinyllama"

model = AutoModelForCausalLM.from_pretrained(base_model_id, torch_dtype=torch.float16)
model = PeftModel.from_pretrained(model, lora_path)
model = model.merge_and_unload()

model.save_pretrained(save_path)
from transformers import AutoTokenizer

# This will download and save tokenizer files in the same folder
AutoTokenizer.from_pretrained("TinyLlama/TinyLlama-1.1B-Chat-v1.0", trust_remote_code=True).save_pretrained("./merged-tinyllama")