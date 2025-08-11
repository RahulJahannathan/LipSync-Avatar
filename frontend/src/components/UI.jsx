import { useRef, useState ,useEffect} from "react";
import { useChat } from "../hooks/useChat";
//import Character from "Character";
import Character from "./Character";
export const UI = ({ hidden, ...props }) => {
  const input = useRef();
  const {
    chat,
    loading,
    cameraZoomed,
    setCameraZoomed,
    message,
    toggleRecording,
    isRecording,
  } = useChat();

  const [showDialog, setShowDialog] = useState(false);

  const sendMessage = () => {
    const text = input.current.value;
    if (!loading && !message) {
      chat(text);
      input.current.value = "";
    }
  };

  if (hidden) return null;
  const [name, setName] = useState("Tessa")

  useEffect(() => {
    const updateName = () => {
      const stored = localStorage.getItem("selectedCostume")
      if (stored) {
        const parsed = JSON.parse(stored)
        const got_id = parsed.id

        if (got_id >= 9 && got_id <= 15) {
          setName("Hardin")
        } else {
          setName("Tessa")
        }
      }
    }

    // Load initial name from localStorage
    updateName()

    // Listen for costume change events
    window.addEventListener("costumeChange", updateName)
    return () => {
      window.removeEventListener("costumeChange", updateName)
    }
  }, [])

  return (
    <>
      <div className="fixed top-0 left-0 right-0 bottom-0 z-10 flex justify-between p-4 flex-col pointer-events-none">
        <div className="self-start backdrop-blur-md bg-white bg-opacity-50 p-4 rounded-lg">
          <h1 className="font-black text-xl">{name}</h1>
          <p>I am here to assist you</p>
        </div>

        <div className="w-full flex flex-col items-end justify-center gap-4">
          {/* NEW: Character Switch Button */}
          <button
            onClick={() => setShowDialog(true)}
            className="pointer-events-auto bg-blue-500 hover:bg-blue-600  text-white p-4 rounded-md"
            title="Change character"
          >
            <h1>
            🎭
            </h1>
          </button>

          {/* Existing Zoom Button */}
          <button
            onClick={() => setCameraZoomed(!cameraZoomed)}
            className="pointer-events-auto bg-blue-500 hover:bg-blue-600 text-white p-4 rounded-md"
          >
            {cameraZoomed ? (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-6 h-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607zM13.5 10.5h-6"
                />
              </svg>
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
                className="w-6 h-6"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607zM10.5 7.5v6m3-3h-6"
                />
              </svg>
            )}
          </button>

          {/* Existing Green Screen Button */}
          <button
            onClick={() => {
              document.querySelector("body").classList.toggle("greenScreen");
            }}
            className="pointer-events-auto bg-blue-500 hover:bg-blue-600 text-white p-4 rounded-md"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path
                strokeLinecap="round"
                d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a.25 2.25 0 002.25 2.25z"
              />
            </svg>
          </button>
        </div>

        {/* Chat Input */}
        <div className="flex items-center gap-2 pointer-events-auto max-w-screen-sm w-full mx-auto">
          <input
            className="w-full placeholder:text-gray-800 placeholder:italic p-4 rounded-md bg-opacity-50 bg-white backdrop-blur-md"
            placeholder="Type a message..."
            ref={input}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
          />

          <button
            onClick={toggleRecording}
            disabled={loading || message}
            className={`text-white p-4 rounded-md transition-colors duration-200 ${
              isRecording
                ? "bg-[#7C3AED] animate-pulse"
                : "bg-blue-500 hover:bg-blue-600"
            }`}
            title="Toggle voice input"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
              className="w-6 h-6"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 18.75a6.75 6.75 0 006.75-6.75V9a.75.75 0 00-1.5 0v3a5.25 5.25 0 01-10.5 0V9a.75.75 0 00-1.5 0v3a6.75 6.75 0 006.75 6.75zM9.75 3a2.25 2.25 0 114.5 0v6a2.25 2.25 0 11-4.5 0V3z"
              />
            </svg>
          </button>

          <button
            disabled={loading || message}
            onClick={sendMessage}
            className={`bg-blue-500 hover:bg-blue-600 text-white p-4 px-10 font-semibold uppercase rounded-md ${
              loading || message ? "cursor-not-allowed opacity-30" : ""
            }`}
          >
            Send
          </button>
        </div>
      </div>

      {/* Dialog Modal */}
      {showDialog && (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div
      className="bg-white rounded-lg shadow-lg relative p-6 overflow-hidden"
      style={{
        width: "75%",
        height: "80%",
      }}
    >
      {/* Close Button */}
      <button
        onClick={() => setShowDialog(false)}
        className="absolute top-3 right-3 text-gray-500 hover:text-gray-800 text-2xl font-bold"
        aria-label="Close"
      >
        ✕
      </button>

      {/* Scrollable Content */}
      <div className="h-full overflow-y-auto pr-2">
        <Character onClose={() => setShowDialog(false)} />
      </div>
    </div>
  </div>
)}


    </>
  );
};
