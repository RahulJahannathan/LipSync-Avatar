import { exec } from "child_process";
import cors from "cors";
import dotenv from "dotenv";
import express from "express";
import { promises as fs } from "fs";
import voice from "elevenlabs-node";
import { GoogleGenerativeAI } from "@google/generative-ai";

dotenv.config(); // ✅ Load environment variables first

const app = express();
app.use(cors());
app.use(express.json());

// ✅ Initialize genAI first, then use it to create the model
const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const gemini = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

app.post("/chat", async (req, res) => {
  try {
    const { message } = req.body;

    if (!message) return res.status(400).json({ error: "Message is required" });

    console.log("Prompt received from UI:", message);

    const prompt = `
You are an AI assistant that responds with realistic facial expressions and animations.

Respond to this message: "${message}"

Return only JSON in the following format (no explanation):

[
  {
    "text": "<your reply sentence>",
    "facialExpression": "smile | neutral | angry | sad | surprised",
    "animation": "Talking_0 | Talking_1 | Idle | Blink"
  }
]
`;

    const result = await gemini.generateContent(prompt);
    const raw = await result.response.text();

    console.log("Raw Gemini response:", raw);

    // Extract clean JSON block from Gemini response
    let cleaned = raw.trim();
    if (cleaned.startsWith("```")) {
      cleaned = cleaned.replace(/```json|```/g, "").trim();
    }

    console.log("Cleaned JSON block:", cleaned);

    const parsed = JSON.parse(cleaned); // <-- may throw if invalid
    if (!Array.isArray(parsed)) {
      return res.status(500).json({ error: "Expected an array of messages" });
    }

    return res.json({ messages: parsed }); // ✅ FRONTEND EXPECTS `messages: []`
  } catch (error) {
    console.error("Error in /chat:", error);
    return res.status(500).json({ error: "Internal server error" });
  }
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});
