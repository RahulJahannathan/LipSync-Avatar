// server.js
import cors from "cors";
import express from "express";
import { promises as fs } from "fs";

const app = express();
app.use(express.json());
app.use(cors());

const port = 3000;

const audioFileToBase64 = async (file) => {
  const data = await fs.readFile(file);
  return data.toString("base64");
};

const readJsonTranscript = async (file) => {
  const data = await fs.readFile(file, "utf8");
  return JSON.parse(data);
};

// Route returns dummy lipsync + audio
app.post("/chat", async (req, res) => {
  const message = req.body.message;

  // Always return dummy response
  const audio64 = await audioFileToBase64("audios/message_0.wav");
  const lipsync = await readJsonTranscript("audios/message_0.json");

  res.send({
    messages: [
      {
        text: message || "Dummy input received",
        audio: audio64,
        lipsync,
        facialExpression: "neutral",
        animation: "Idle", // Optional: You can keep it "Idle" or remove this line
      },
    ],
  });
});

app.listen(port, () => {
  console.log(`Lipsync-only backend running at http://localhost:${port}`);
});
