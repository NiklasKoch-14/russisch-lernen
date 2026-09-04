from dataclasses import dataclass
from sqlite3 import Connection, Row


@dataclass
class SrsState:
    lexeme_id: str
    form_key: str
    interval_days: float
    ease_factor: float
    repetitions: int
    due_date: str


def _row(row: Row) -> SrsState:
    return SrsState(
        lexeme_id=row["lexeme_id"],
        form_key=row["form_key"],
        interval_days=row["interval_days"],
        ease_factor=row["ease_factor"],
        repetitions=row["repetitions"],
        due_date=row["due_date"],
    )


def get_state(conn: Connection, *, lexeme_id: str, form_key: str) -> SrsState | None:
    row = conn.execute(
        "SELECT * FROM lexeme_srs WHERE lexeme_id = ? AND form_key = ?", (lexeme_id, form_key)
    ).fetchone()
    return _row(row) if row else None


def upsert_state(conn: Connection, state: SrsState) -> None:
    conn.execute(
        "INSERT INTO lexeme_srs (lexeme_id, form_key, interval_days, ease_factor, repetitions,"
        " due_date) VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(lexeme_id, form_key) DO UPDATE SET"
        " interval_days = excluded.interval_days, ease_factor = excluded.ease_factor,"
        " repetitions = excluded.repetitions, due_date = excluded.due_date",
        (
            state.lexeme_id,
            state.form_key,
            state.interval_days,
            state.ease_factor,
            state.repetitions,
            state.due_date,
        ),
    )
    conn.commit()


def due_states(conn: Connection, *, today: str, limit: int = 20) -> list[SrsState]:
    rows = conn.execute(
        "SELECT * FROM lexeme_srs WHERE due_date <= ?"
        " ORDER BY due_date, lexeme_id, form_key LIMIT ?",
        (today, limit),
    ).fetchall()
    return [_row(row) for row in rows]
