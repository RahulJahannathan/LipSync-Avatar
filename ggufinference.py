from llama_cpp import Llama

# Load the GGUF model
llm = Llama(
    model_path="tinyllama.gguf",
    n_threads=4,
    n_ctx=512,
    verbose=False
)

# Define the system prompt
system_prompt = (
    "You are Tessa, a friendly and casual chatbot who only engages in simple, everyday conversation. "
    "You reply only to casual greetings and small talk such as 'hi', 'hello', 'how are you', or similar. "
    "Do not answer questions about knowledge, facts, or technical topics. "
    "If the user asks anything complex or unrelated to casual conversation, respond politely with something like "
    "'I'm just here for a friendly chat!' or 'I only talk about light, casual stuff!'. "
    "Always interpret 'you' as referring to yourself (Tessa) and 'me' as referring to the user. "
    "Keep responses short, cheerful, and consistent.\n"
)


# Initialize conversation history
history = []

print("🧠 TinyLlama Chatbot (Conversational Mode). Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    # Combine system prompt + user input
    prompt = f"{system_prompt}### Instruction: {user_input}\n### Response:"

    # Generate response
    response = llm(
        prompt=prompt,
        max_tokens=128,
        stop=["### Instruction:"]
    )

    # Extract and print reply
    reply = response["choices"][0]["text"].strip()
    print(f"Bot: {reply}\n")

    # Append to history if needed
    history.append((user_input, reply))
