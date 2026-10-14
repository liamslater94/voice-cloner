"""Saigon Tutor: a personal Southern Vietnamese tutor powered by Claude.

Run with:  uvicorn app:app --reload
"""

import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent
DB_PATH = Path(os.environ.get("TUTOR_DB", BASE_DIR / "tutor.db"))
MODEL = os.environ.get("TUTOR_MODEL", "claude-opus-5-5")
HISTORY_LIMIT = 40  # messages of conversation sent to Claude each turn
LEVELS = {"beginner", "intermediate", "advanced"}

TUTOR_PROMPT = (BASE_DIR / "tutor_prompt.md").read_text(encoding="utf-8")

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "reply_vi": {"type": "string"},
        "reply_en": {"type": "string"},
        "correction": {"type": "string"},
        "pronunciation_tip": {"type": "string"},
        "new_words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "vi": {"type": "string"},
                    "en": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["vi", "en", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["reply_vi", "reply_en", "correction", "pronunciation_tip", "new_words"],
    "additionalProperties": False,
}

client = anthropic.Anthropic()
app = FastAPI(title="Saigon Tutor")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(db()) as conn, conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS vocab (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vi TEXT NOT NULL UNIQUE,
                en TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                times_seen INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )


init_db()


class ChatRequest(BaseModel):
    text: str
    level: str = "beginner"


def load_history(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (HISTORY_LIMIT,)
    ).fetchall()
    history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    # The API requires the conversation to start with a user turn.
    while history and history[0]["role"] != "user":
        history.pop(0)
    return history


def student_context(conn: sqlite3.Connection, level: str) -> str:
    words = conn.execute("SELECT vi, en FROM vocab ORDER BY id DESC LIMIT 150").fetchall()
    known = ", ".join(f"{w['vi']} ({w['en']})" for w in words) or "none yet"
    return f"Student level: {level}.\nWords the student has already met: {known}."


@app.post("/api/chat")
def chat(req: ChatRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(400, "Empty message")
    level = req.level if req.level in LEVELS else "beginner"

    with closing(db()) as conn:
        messages = load_history(conn) + [{"role": "user", "content": text}]
        system = [
            # Stable tutor instructions first so they are prompt-cached.
            {"type": "text", "text": TUTOR_PROMPT, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": student_context(conn, level)},
        ]

    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            system=system,
            messages=messages,
            output_config={
                "effort": "low",  # chat: keep replies fast
                "format": {"type": "json_schema", "schema": REPLY_SCHEMA},
            },
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise HTTPException(500, "Invalid or missing ANTHROPIC_API_KEY")
    except anthropic.RateLimitError:
        raise HTTPException(429, "Rate limited by the Claude API, try again shortly")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"Claude API error: {e.message}")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "Could not reach the Claude API")

    if response.stop_reason == "refusal":
        raise HTTPException(422, "The tutor declined to answer that message")
    if response.stop_reason == "max_tokens":
        raise HTTPException(502, "The reply was cut off, please try again")

    raw = next(b.text for b in response.content if b.type == "text")
    reply = json.loads(raw)

    with closing(db()) as conn, conn:
        conn.execute("INSERT INTO messages (role, content) VALUES ('user', ?)", (text,))
        conn.execute("INSERT INTO messages (role, content) VALUES ('assistant', ?)", (raw,))
        for w in reply["new_words"]:
            conn.execute(
                """INSERT INTO vocab (vi, en, note) VALUES (?, ?, ?)
                   ON CONFLICT(vi) DO UPDATE SET times_seen = times_seen + 1""",
                (w["vi"].strip(), w["en"].strip(), w["note"].strip()),
            )
    return reply


@app.get("/api/history")
def history():
    with closing(db()) as conn:
        rows = conn.execute("SELECT role, content FROM messages ORDER BY id").fetchall()
    out = []
    for r in rows:
        if r["role"] == "assistant":
            out.append({"role": "assistant", "reply": json.loads(r["content"])})
        else:
            out.append({"role": "user", "text": r["content"]})
    return out


@app.get("/api/vocab")
def vocab():
    with closing(db()) as conn:
        rows = conn.execute(
            "SELECT id, vi, en, note, times_seen FROM vocab ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


@app.delete("/api/vocab/{word_id}")
def delete_word(word_id: int):
    with closing(db()) as conn, conn:
        conn.execute("DELETE FROM vocab WHERE id = ?", (word_id,))
    return {"ok": True}


@app.post("/api/reset")
def reset_conversation():
    """Start a new conversation. Vocabulary is kept."""
    with closing(db()) as conn, conn:
        conn.execute("DELETE FROM messages")
    return {"ok": True}


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")
