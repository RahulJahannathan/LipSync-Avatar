from llama_cpp import Llama

llm = Llama(
    model_path="tinyllama.gguf",
    n_threads=4,
    n_ctx=512,
    verbose=False
)

print("🧠 TinyLlama Chatbot (streaming). Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    prompt = f"### Instruction: {user_input}\n### Response:"

    print("Bot: ", end="", flush=True)
    for output in llm(
        prompt=prompt,
        max_tokens=256,
        stop=["### Instruction:"],
        temperature=0.7,
        stream=True  # This is the key
    ):
        token = output["choices"][0]["text"]
        print(token, end="", flush=True)  # print each token as it comes
