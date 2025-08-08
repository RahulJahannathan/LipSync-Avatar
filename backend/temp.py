# backend/main.py

from llm.tessa_chatbot import tessa

response = tessa.get_response("hi")
print(response)
