import { exec } from "child_process";
import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import { promises as fs } from "fs";
import voice from "elevenlabs-node";
import { GoogleGenerativeAI } from "@google/generative-ai";

dotenv.config();

const geminiApiKey = process.env.GEMINI_API_KEY;
const elevenLabsApiKey = process.env.ELEVEN_LABS_API_KEY;
const voiceID = "JBFqnCBsd6RMkjVDRZzb";

const genAI = new GoogleGenerativeAI(geminiApiKey);
const app = express();
app.use(cors());
app.use(express.json());

app.get("/", (req, res) => {
  res.send("Hello World!");
});

app.get("/voices", async (req, res) => {
  res.send(await voice.getVoices(elevenLabsApiKey));
});

const execCommand = (command) => {
  return new Promise((resolve, reject) => {
    exec(command, (error, stdout, stderr) => {
      if (error) reject(error);
      resolve(stdout);
    });
  });
};

const audioFileToBase64 = async (filePath) => {
  const audioBuffer = await fs.readFile(filePath);
  return `data:audio/mp3;base64,${audioBuffer.toString("base64")}`;
};

const readJsonTranscript = async (jsonPath) => {
  const data = await fs.readFile(jsonPath, "utf-8");
  return JSON.parse(data);
};

const lipSyncMessage = async (messageIndex) => {
  const time = new Date().getTime();
  console.log(`Starting conversion for message ${messageIndex}`);
  await execCommand(
    `ffmpeg -y -i audios/message_${messageIndex}.mp3 audios/message_${messageIndex}.wav`
  );
  console.log(`Conversion done in ${new Date().getTime() - time}ms`);
  await execCommand(
    `rhubarb -f json -o audios/message_${messageIndex}.json audios/message_${messageIndex}.wav -r phonetic`
  );
  console.log(`Lip sync done in ${new Date().getTime() - time}ms`);
};

app.post("/chat", async (req, res) => {
  try {
    const { message } = req.body;

    if (!message) return res.status(400).json({ error: "Message is required" });

    console.log("Prompt received from UI:", message);

    // Check API Keys
    if (!elevenLabsApiKey || !geminiApiKey) {
      const messages = [
        {
          text: "Please my dear, don't forget to add your API keys!",
          audio: await audioFileToBase64("audios/api_0.wav"),
          lipsync: await readJsonTranscript("audios/api_0.json"),
          facialExpression: "angry",
          animation: "Angry",
        },
        {
          text: "You don't want to ruin Wawa Sensei with a crazy Gemini and ElevenLabs bill, right?",
          audio: await audioFileToBase64("audios/api_1.wav"),
          lipsync: await readJsonTranscript("audios/api_1.json"),
          facialExpression: "smile",
          animation: "Laughing",
        },
      ];
      return res.send({ messages });
    }

    const model = genAI.getGenerativeModel({ model: "gemini-2.5-flash" });

    const systemPrompt = `
You are a virtual girlfriend.
You will always reply with a JSON array of messages. With a maximum of 3 messages.
Each message has a text, facialExpression, and animation property.
The different facial expressions are: smile, sad, angry, surprised, funnyFace, and default.
The different animations are: Talking_0, Talking_1, Talking_2, Crying, Laughing, Rumba, Idle, Terrified, and Angry.
Respond with JSON only. Do not include any Markdown formatting or explanations. Output format: [{ text: ..., facialExpression: ..., animation: ... }]
`;

    const result = await model.generateContent({
      contents: [
        {
          role: "user",
          parts: [{ text: `${systemPrompt}\n\nUser: ${message}` }],
        },
      ],
    });

    const rawText = await result.response.text();
    const jsonText = extractJsonFromCodeBlock(rawText);
    let messages;

    try {
      messages = JSON.parse(jsonText);
    } catch (e) {
      console.error("❌ Failed to parse Gemini response:", jsonText);
      return res.status(500).send({ error: "Invalid Gemini JSON response" });
    }

    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      const fileName = `audios/message_${i}.mp3`;
      const textInput = msg.text || "Hi, I'm your avatar. How are you?";
      console.log(`Generating audio for message ${i}:`, textInput);

      await voice.textToSpeech(elevenLabsApiKey, voiceID, fileName, textInput);
      await lipSyncMessage(i);
      msg.audio = await audioFileToBase64(fileName);
      msg.lipsync = await readJsonTranscript(`audios/message_${i}.json`);
    }

    res.send({ messages });

  } catch (err) {
    console.error("❌ Error in /chat:", err);
    res.status(500).send({ error: "Internal server error" });
  }
});

const extractJsonFromCodeBlock = (text) => {
  const match = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/);
  return match ? match[1] : text;
};

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
