# Saigon Tutor

A personal AI tutor for **Southern (Saigon) Vietnamese**, built on the Claude API.

## Non-negotiables
- Everything the tutor teaches is **Southern Vietnamese** (heo not lợn, bắp not ngô, ly not cốc,
  muỗng not thìa, chén not bát, trái not quả, ba/má not bố/mẹ, tui, hông, nha/nè/hen...).
  The dialect rules live in `tutor_prompt.md`; change them there, not in code.
- Never commit API keys. Secrets come from environment variables (see `.env.example`).

## Layout
- `app.py`: FastAPI backend. `/api/chat` calls Claude with structured JSON output
  (`REPLY_SCHEMA`), stores the conversation and new vocabulary in SQLite (`tutor.db`).
- `tutor_prompt.md`: the tutor's persona, dialect rules and teaching style (prompt-cached).
- `static/index.html`: single-page UI, no build step. Speech-to-text and text-to-speech use the
  browser's built-in Web Speech API (`vi-VN`) for now.

## Run
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=...
    uvicorn app:app --reload   # then open http://localhost:8000
