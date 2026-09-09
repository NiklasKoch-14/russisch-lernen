import datetime as dt
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.srs.sm2 import MAX_INTERVAL_DAYS

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    language TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    created_at TEXT NOT NULL,
    show_transliteration INTEGER NOT NULL DEFAULT 1,
    audio_autoplay INTEGER NOT NULL DEFAULT 1,
    placement_unit INTEGER
);

CREATE TABLE IF NOT EXISTS learning_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    session_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES conversation_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES conversation_sessions(id),
    updated_level TEXT,
    notable_errors_json TEXT NOT NULL,
    vocab_suggestions_json TEXT NOT NULL,
    next_topics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    term TEXT NOT NULL,
    translation TEXT NOT NULL,
    example_sentence TEXT NOT NULL,
    source_session_id INTEGER REFERENCES conversation_sessions(id),
    interval_days REAL NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    repetitions INTEGER NOT NULL DEFAULT 0,
    due_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES vocab_cards(id),
    user_answer TEXT NOT NULL,
    correct INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS unit_progress (
    unit_id       INTEGER PRIMARY KEY,
    status        TEXT NOT NULL,
    correct_count INTEGER NOT NULL DEFAULT 0,
    total_count   INTEGER NOT NULL DEFAULT 0,
    completed_at  TEXT
);

CREATE TABLE IF NOT EXISTS exercise_attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id     INTEGER NOT NULL,
    exercise_id TEXT NOT NULL,
    correct     INTEGER NOT NULL,
    answer_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lexeme_srs (
    lexeme_id     TEXT NOT NULL,
    form_key      TEXT NOT NULL,
    interval_days REAL NOT NULL DEFAULT 0,
    ease_factor   REAL NOT NULL DEFAULT 2.5,
    repetitions   INTEGER NOT NULL DEFAULT 0,
    due_date      TEXT NOT NULL,
    PRIMARY KEY (lexeme_id, form_key)
);

CREATE TABLE IF NOT EXISTS screening_results (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    answers_json   TEXT NOT NULL,
    placement_unit INTEGER NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS game_scene_runs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    scene_id  TEXT NOT NULL,
    seed      TEXT NOT NULL,
    played_at TEXT NOT NULL
);
"""

PROFILE_COLUMNS = {
    "show_transliteration": "INTEGER NOT NULL DEFAULT 1",
    "placement_unit": "INTEGER",
    "audio_autoplay": "INTEGER NOT NULL DEFAULT 1",
}


def _ensure_profile_columns(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the first release to an existing profile table."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(profile)")}
    for name, definition in PROFILE_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE profile ADD COLUMN {name} {definition}")


def _cap_runaway_intervals(conn: sqlite3.Connection) -> None:
    """Deckle Wiederholungsabstände aus der Zeit vor `MAX_INTERVAL_DAYS`.

    Dort wuchs das Intervall bei jeder richtigen Antwort weiter; jenseits von
    rund 2,9 Millionen Tagen sprengt der Termin den Datumsbereich, und die
    Antwort scheiterte mit 500. Betroffene Zeilen bekommen den Deckel und einen
    erreichbaren Termin — sonst kämen ihre Wörter nie wieder an die Reihe.
    """
    due = (dt.date.today() + dt.timedelta(days=MAX_INTERVAL_DAYS)).isoformat()
    conn.execute(
        "UPDATE lexeme_srs SET interval_days = ?, due_date = ? WHERE interval_days > ?",
        (MAX_INTERVAL_DAYS, due, MAX_INTERVAL_DAYS),
    )


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        _ensure_profile_columns(conn)
        _cap_runaway_intervals(conn)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session(db_path: str):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
