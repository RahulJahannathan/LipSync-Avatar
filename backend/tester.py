import asyncio
import websockets
import json

async def test_simple_server():
    uri = "ws://localhost:3000/ws"  # For test_ws.py
    async with websockets.connect(uri) as ws:
        print("Connected to simple server.")
        print("Server says:", await ws.recv())

        await ws.send("Hello from tester!")
        print("Echo:", await ws.recv())

async def test_main_ws():
    uri = "ws://localhost:3000/ws/chat"  # For main_ws.py
    async with websockets.connect(uri) as ws:
        print("Connected to main_ws.py server.")

        # Step 1: send hello
        await ws.send(json.dumps({"type": "hello", "session_id": "test123"}))
        print("Hello ACK:", await ws.recv())

        # Step 2: send user text
        await ws.send(json.dumps({"type": "user_text", "message": "Hi there!", "name": "tessa"}))

        # Step 3: read streaming messages until done
        while True:
            msg = await ws.recv()
            print("Received:", msg)
            if '"type": "done"' in msg:
                break

async def main():
    print("Choose test:")
    print("1. Simple test_ws.py server")
    print("2. main_ws.py server")
    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        await test_simple_server()
    elif choice == "2":
        await test_main_ws()
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    asyncio.run(main())
