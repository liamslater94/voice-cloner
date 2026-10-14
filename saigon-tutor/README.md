# Saigon Tutor 🇻🇳

A personal AI tutor for **Southern Vietnamese**, the way people actually talk in Sài Gòn.
You chat (typed or spoken) with "Cô Lan", a friendly Saigon tutor powered by Claude. She:

- replies in Vietnamese pitched at your level, with an English translation on tap
- gently corrects your mistakes, and flags Northern words with their Southern equivalent
- gives Southern pronunciation tips (hỏi/ngã merge, v/d/gi → "y", -n/-ng merge, ...)
- builds your vocabulary notebook automatically and reuses words you've met
- reads her replies aloud (with a slow mode), and lets you answer by speaking

## Quick start

```bash
cd saigon-tutor
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # from https://platform.claude.com
uvicorn app:app --reload
```

Open http://localhost:8000 in **Chrome** (desktop or Android). Chrome has the best support for
the Vietnamese speech recognition the 🎤 button uses. Safari works for typing and playback.

To use it on your phone around Saigon, run it on your laptop and open
`http://<laptop-ip>:8000` (start uvicorn with `--host 0.0.0.0`), or deploy it (see roadmap).
The mic needs HTTPS when the page isn't on `localhost`.

## About the voice

Version 1 uses your browser/OS's built-in Vietnamese voice, which is free but usually
sounds **Northern**. Getting a natural Saigon voice is the main next step, see the roadmap.

## Roadmap

1. **Southern voice.** Replace `speak()` in `static/index.html` with a server-side TTS endpoint:
   a cloud voice with a Southern accent, or a voice cloned (with consent!) from a Saigonese
   speaker via a Vietnamese-capable model. Voicebox in this repo could host it as a new engine.
2. **Better speech recognition.** Send recorded audio to Whisper (e.g. Voicebox's `/transcribe`)
   instead of the browser recognizer, and compare it with what you meant to say for
   pronunciation feedback.
3. **Spaced-repetition review** of the vocab notebook (flashcards with audio).
4. **Scenario lessons**: ordering at a quán, Grab, bargaining at Chợ Bến Thành, renting a room.
5. **Deploy** (Fly.io, Railway or Render) with a password so you can use it on 4G.
