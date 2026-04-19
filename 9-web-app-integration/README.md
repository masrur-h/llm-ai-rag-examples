# Message Rewriter

## Project Description
Message Rewriter is a simple AI-powered web application that rewrites a user's message in a selected tone. The user enters a message, chooses a tone such as Professional, Friendly, Formal, Casual, or Confident, and the app returns a rewritten version using the Gemini API.

## Architecture Overview
React frontend → FastAPI backend → Gemini API

The React frontend collects the user's text and selected tone. It sends a POST request to the FastAPI backend. The backend creates a prompt, sends it to Gemini, and returns the rewritten message to the frontend.

## Technical Choices
- **React + Vite** for the frontend because it is fast and simple for building the user interface.
- **FastAPI** for the backend because it is lightweight and easy to use for building API endpoints.
- **Gemini API** as the LLM provider because it has a free tier and was already familiar from course exercises.
- **Single-turn design** because this project is intended to be a Level 1 application with one input and one response.
- **Backend API call** instead of calling Gemini directly from the frontend, so the API key stays hidden.

## Setup and Running Instructions

### Backend
1. Open a terminal in the `backend` folder.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
3. Run uvicorn main:app

### Frontend
1. Run npm install
2. Run npm run dev