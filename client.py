import requests
import json
import time

# Input prompt
user_input = "Hi, how are you?"

# Endpoint URL
url = "http://127.0.0.1:8000/chat"

# JSON payload
payload = {"user_input": user_input}

# Send request
start_time = time.time()
response = requests.post(url, json=payload)
end_time = time.time()

# Print results
print("Response:", response.json())
print(f"Total time taken: {end_time - start_time:.2f} seconds")
