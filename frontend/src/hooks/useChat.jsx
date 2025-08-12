import { createContext, useContext, useEffect, useRef, useState } from "react";

const backendUrl = "http://localhost:3000";

const ChatContext = createContext();

export const ChatProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState();
  const [loading, setLoading] = useState(false);
  const [cameraZoomed, setCameraZoomed] = useState(true);
  const [isRecording, setIsRecording] = useState(false);

  // ✅ New: store LLM raw text for live display
  const [liveText, setLiveText] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  // Helper function to get the character name from localStorage
  const getCharacterName = () => {
    let name = "Tessa"; // default
    const stored = localStorage.getItem("selectedCostume");
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.id >= 9 && parsed.id <= 15) {
        name = "Hardin";
      }
    }
    return name;
  };

  const chat = async (message) => {
    try {
      setLoading(true);
      const name = getCharacterName();

      const response = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, name }), // send name too
      });

      const resp = await response.json();
      const newMessages = Array.isArray(resp) ? resp : resp.messages || [];

      // ✅ If text exists, store it separately for live display
      if (newMessages.length > 0 && newMessages[0].text) {
        setLiveText(newMessages[0].text);
        console.log(liveText,'from hook')
      }

      setMessages((prev) => [...prev, ...newMessages]);
    } catch (err) {
      console.error("Chat fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const sendAudioToBackend = async (audioBlob) => {
    const formData = new FormData();
    const name = getCharacterName();
    formData.append("file", audioBlob, "voice.webm");
    formData.append("name", name); // send name in form data

    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/voice`, {
        method: "POST",
        body: formData,
      });

      const resp = await response.json();
      const newMessages = Array.isArray(resp) ? resp : resp.messages || [];

      // ✅ Store LLM text for live display
      if (newMessages.length > 0 && newMessages[0].text) {
        setLiveText(newMessages[0].text);
      }

      setMessages((prev) => [...prev, ...newMessages]);
    } catch (err) {
      console.error("Voice fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== "inactive") {
        recorder.stop();
      }
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        mediaRecorderRef.current = recorder;
        audioChunksRef.current = [];
        setIsRecording(true);

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) {
            audioChunksRef.current.push(e.data);
          }
        };

        recorder.onstop = () => {
          setIsRecording(false);
          const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          sendAudioToBackend(audioBlob);
          stream.getTracks().forEach((track) => track.stop());
        };

        recorder.start();
      } catch (err) {
        console.error("Mic error:", err);
        setIsRecording(false);
      }
    }
  };

  const onMessagePlayed = () => {
    setMessages((prev) => prev.slice(1));
  };

  useEffect(() => {
    setMessage(messages.length > 0 ? messages[0] : null);
  }, [messages]);

  return (
    <ChatContext.Provider
      value={{
        chat,
        message,
        messages,
        liveText, // ✅ make live text accessible
        setLiveText, // optional: if you want to clear or update manually
        onMessagePlayed,
        loading,
        cameraZoomed,
        setCameraZoomed,
        toggleRecording,
        isRecording,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
};
