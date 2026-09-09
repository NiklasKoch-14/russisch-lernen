import sqlite3

from app.db import get_connection, init_db
from app.srs.sm2 import MAX_INTERVAL_DAYS

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
    assert {"show_transliteration", "placement_unit", "audio_autoplay"} <= _columns(
        conn, "profile"
    )
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    assert row["cefr_level"] == "A2"
    assert row["show_transliteration"] == 1
    assert row["placement_unit"] is None
    assert row["audio_autoplay"] == 1
    conn.close()


def test_init_db_is_idempotent(tmp_path):
    path = str(tmp_path / "twice.db")
    init_db(path)
    init_db(path)
    conn = get_connection(path)
    assert len(_columns(conn, "profile")) == 7
    conn.close()


def test_init_db_caps_runaway_intervals_from_older_databases(tmp_path):
    """Datenbanken aus der Zeit ohne Deckel tragen unerreichbare Termine.

    Sie waren der Grund, warum eine richtige Antwort mit 500 endete; ohne
    Aufräumen käme jedes betroffene Wort nie wieder zur Wiederholung.
    """
    path = str(tmp_path / "runaway.db")
    init_db(path)
    conn = get_connection(path)
    conn.execute(
        "INSERT INTO lexeme_srs (lexeme_id, form_key, interval_days, ease_factor,"
        " repetitions, due_date) VALUES ('eto', 'base', 9000000.0, 2.5, 30, '9999-12-31')"
    )
    conn.execute(
        "INSERT INTO lexeme_srs (lexeme_id, form_key, interval_days, ease_factor,"
        " repetitions, due_date) VALUES ('ne', 'base', 6.0, 2.5, 2, '2026-09-15')"
    )
    conn.commit()
    conn.close()

    init_db(path)

    conn = get_connection(path)
    rows = {row["lexeme_id"]: row for row in conn.execute("SELECT * FROM lexeme_srs")}
    assert rows["eto"]["interval_days"] == MAX_INTERVAL_DAYS
    assert rows["eto"]["due_date"] < "9999-01-01"
    # Gesunde Zeilen bleiben unangetastet.
    assert rows["ne"]["interval_days"] == 6.0
    assert rows["ne"]["due_date"] == "2026-09-15"
    conn.close()
