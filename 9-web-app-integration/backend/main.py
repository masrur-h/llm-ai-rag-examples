import os

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set — copy .env.example to .env and add your key")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

app = FastAPI(title="Message Rewriter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TONES = {
    "Professional",
    "Friendly",
    "Formal",
    "Casual",
    "Confident",
}


class RewriteRequest(BaseModel):
    text: str
    tone: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/rewrite")
async def rewrite_message(request: RewriteRequest):
    text = request.text.strip()
    tone = request.tone.strip()

    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    if tone not in ALLOWED_TONES:
        raise HTTPException(status_code=400, detail="Invalid tone selected.")

    prompt = f"""
You are a helpful message rewriting assistant.

Rewrite the user's message in a {tone.lower()} tone.

Rules:
- Keep the original meaning.
- Do not add new facts.
- Do not explain your changes.
- Return only the rewritten message.
- Keep it concise and natural.
- Keep names, dates, and important details unchanged unless grammar requires minor fixes.

User message:
{text}
"""

    response = model.generate_content(prompt)

    return {
        "rewritten_text": response.text.strip()
    }