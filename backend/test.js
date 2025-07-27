import dotenv from "dotenv";
dotenv.config();

import { GoogleGenerativeAI } from "@google/generative-ai";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

async function run() {
  const model = genAI.getGenerativeModel({ model: "gemini-2.0-flash" });

  const result = await model.generateContent("Say something as a girlfriend");
  const response = await result.response;
  const text = response.text();

  console.log("Gemini Output:\n", text);
}

run().catch(console.error);
