import sqlite3

from app.db import get_connection, init_db

OLD_PROFILE_SCHEMA = """
CREATE TABLE profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    language TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_init_db_creates_new_tables(tmp_path):
    path = str(tmp_path / "new.db")
    init_db(path)
    conn = get_connection(path)
    names = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"unit_progress", "exercise_attempts", "lexeme_srs", "screening_results"} <= names
    conn.close()


def test_init_db_adds_missing_profile_columns_to_old_database(tmp_path):
    path = str(tmp_path / "old.db")
    legacy = sqlite3.connect(path)
    legacy.executescript(OLD_PROFILE_SCHEMA)
    legacy.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at)"
        " VALUES (1, 'english', 'A2', '2026-01-01')"
    )
    legacy.commit()
    legacy.close()

    init_db(path)

    conn = get_connection(path)
    assert {"show_transliteration", "placement_unit"} <= _columns(conn, "profile")
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    assert row["cefr_level"] == "A2"
    assert row["show_transliteration"] == 1
    assert row["placement_unit"] is None
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    path = str(tmp_path / "twice.db")
    init_db(path)
    init_db(path)
    conn = get_connection(path)
    assert len(_columns(conn, "profile")) == 6
    conn.close()
