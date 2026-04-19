# Message Rewriter – Presentation Notes

## What my app does
My project is an AI-powered Message Rewriter.  
The user pastes a message, chooses a tone, and the app rewrites the message in that tone using Gemini.

## Why this is Level 1
This is a Level 1 project because it is a single-turn application:
- one user input
- one backend request
- one LLM response

It does not use:
- conversation memory
- file upload
- retrieval
- tool use
- multi-step orchestration

## Architecture
React frontend → FastAPI backend → Gemini API

## Frontend role
The frontend collects:
- the user's message
- the selected tone

It sends them as a POST request to the backend and displays the rewritten result.

## Backend role
The backend:
- receives the text and tone
- validates the input
- builds a prompt
- sends the prompt to Gemini
- returns the rewritten text

## Why I used a backend
I used a backend so the API key is not exposed in the frontend.

## Prompt logic
The prompt tells Gemini to:
- rewrite the message in the selected tone
- keep the original meaning
- not add new facts
- return only the rewritten message

## Technical choices
- React for the UI
- FastAPI for the backend API
- Gemini free API as the LLM provider
- simple single-turn design to match Level 1

## Limitations
- no memory or conversation history
- depends on internet and external API
- output can vary slightly
- no authentication or database
- built for local demo, not public production use