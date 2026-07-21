import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class ConversationTurn:
    role: str
    content: str


def create_session(conn: Connection, *, language: str, session_type: str) -> int:
    started_at = dt.datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO conversation_sessions (language, session_type, started_at) VALUES (?, ?, ?)",
        (language, session_type, started_at),
    )
    conn.commit()
    return cursor.lastrowid


def end_session(conn: Connection, *, session_id: int) -> None:
    conn.execute(
        "UPDATE conversation_sessions SET ended_at = ? WHERE id = ?",
        (dt.datetime.utcnow().isoformat(), session_id),
    )
    conn.commit()


def add_turn(conn: Connection, *, session_id: int, role: str, content: str) -> None:
    conn.execute(
        "INSERT INTO conversation_turns (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, dt.datetime.utcnow().isoformat()),
    )
    conn.commit()


def get_turns(conn: Connection, *, session_id: int) -> list[ConversationTurn]:
    rows = conn.execute(
        "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    return [ConversationTurn(role=row["role"], content=row["content"]) for row in rows]


def get_active_session(conn: Connection, *, language: str, session_type: str) -> int | None:
    row = conn.execute(
        """SELECT id FROM conversation_sessions
           WHERE language = ? AND session_type = ? AND ended_at IS NULL
           ORDER BY id DESC LIMIT 1""",
        (language, session_type),
    ).fetchone()
    return row["id"] if row else None
