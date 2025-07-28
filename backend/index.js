import { exec } from "child_process";
import cors from "cors";
import dotenv from "dotenv";
import voice from "elevenlabs-node";
import express from "express";
import { promises as fs } from "fs";
import path from "path";

dotenv.config();

const elevenLabsApiKey = "sk_e3a4e5c1a3cc2f8d510bc7676fbbd6ff5847d2c60e7bc977";
const voiceID = "21m00Tcm4TlvDq8ikWAM"; // Your ElevenLabs voice ID

const app = express();
app.use(express.json());
app.use(cors());
const port = 3000;

const execCommand = (command) => {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) reject(error);
      resolve(stdout);
    });
  });
};

const audioFileToBase64 = async (file) => {
  const data = await fs.readFile(file);
  return data.toString("base64");
};

const readJsonTranscript = async (file) => {
  const data = await fs.readFile(file, "utf8");
  return JSON.parse(data);
};

const lipSyncMessage = async () => {
  const mp3Path = path.resolve("audios/message.mp3");
  const wavPath = path.resolve("audios/message.wav");
  const jsonPath = path.resolve("audios/message.json");
  const rhubarbPath = path.resolve("bin/rhubarb.exe"); // For Windows

  await execCommand(`ffmpeg -y -i "${mp3Path}" "${wavPath}"`);
  await execCommand(`"${rhubarbPath}" -f json -o "${jsonPath}" "${wavPath}" -r phonetic`);
};

app.post("/chat", async (req, res) => {
  const userMessage = req.body.message;
  if (!userMessage) {
    return res.status(400).json({ error: "No message provided" });
  }

  const mp3Path = path.resolve("audios/message.mp3");

  // Generate audio using ElevenLabs
  await voice.textToSpeech(elevenLabsApiKey, voiceID, mp3Path, userMessage);

  // Run Rhubarb to generate lipsync JSON
  await lipSyncMessage();

  // Return the same user message, audio, and lipsync JSON
  const audio = await audioFileToBase64(mp3Path);
  const lipsync = await readJsonTranscript("audios/message.json");

  res.send({
    messages: [
      {
        text: userMessage,
        audio,
        lipsync,
        facialExpression: "default",
        animation: "Talking_0",
      },
    ],
  });
});

app.listen(port, () => {
  console.log(`✅ Virtual Girlfriend backend running at http://localhost:${port}`);
});
