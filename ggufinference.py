""" import time
from llama_cpp import Llama
import os
os.environ["LLAMA_CPP_LOG_LEVEL"] = "OFF"  # must be set before importing llama_cpp


start_load = time.time()
llm = Llama(model_path="tinyllama.gguf", n_threads=4, n_ctx=512)
end_load = time.time()

start_infer = time.time()
output = llm(
    prompt="### Instruction: Hi, how are you?\n### Response:",
    max_tokens=64,
    stop=["### Instruction:"]
)
print(output["choices"][0]["text"])

end_infer = time.time()

print("Model response:", output["choices"][0]["text"])
print(f"\n⏱️ Model load time: {end_load - start_load:.2f} seconds")
print(f"🧠 Inference time: {end_infer - start_infer:.2f} seconds")
 """
from llama_cpp import Llama

# Load the GGUF model
llm = Llama(
    model_path="tinyllama.gguf",  # Change if your path is different
    n_threads=4,
    n_ctx=512,
    verbose=False
)

# Initialize conversation history
history = []

print("🧠 TinyLlama Chatbot. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    # Format prompt using instruction-style
    prompt = f"### Instruction: {user_input}\n### Response:"

    # Generate model response
    response = llm(
        prompt=prompt,
        max_tokens=128,
        stop=["### Instruction:"]
    )

    # Extract and print reply
    reply = response["choices"][0]["text"].strip()
    print(f"Bot: {reply}\n")

    # Optionally, append to history if needed later
    history.append((user_input, reply))
