import { createContext, useContext, useEffect, useRef, useState } from "react";

const backendUrl = "http://localhost:3000";

const ChatContext = createContext();

export const ChatProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [message, setMessage] = useState();
  const [loading, setLoading] = useState(false);
  const [cameraZoomed, setCameraZoomed] = useState(true);
  const [isRecording, setIsRecording] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const chat = async (message) => {
    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      const resp = await response.json();
      const newMessages = Array.isArray(resp) ? resp : resp.messages || [];
      setMessages((prev) => [...prev, ...newMessages]);
    } catch (err) {
      console.error("Chat fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const sendAudioToBackend = async (audioBlob) => {
    const formData = new FormData();
    formData.append("file", audioBlob, "voice.webm");

    try {
      setLoading(true);
      const response = await fetch(`${backendUrl}/voice`, {
        method: "POST",
        body: formData,
      });

      const resp = await response.json();
      const newMessages = Array.isArray(resp) ? resp : resp.messages || [];
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
