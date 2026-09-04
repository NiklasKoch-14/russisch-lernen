import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection, Row


@dataclass
class UnitProgress:
    unit_id: int
    status: str
    correct_count: int
    total_count: int
    completed_at: str | None


def _row(row: Row) -> UnitProgress:
    return UnitProgress(
        unit_id=row["unit_id"],
        status=row["status"],
        correct_count=row["correct_count"],
        total_count=row["total_count"],
        completed_at=row["completed_at"],
    )


def get_progress(conn: Connection, unit_id: int) -> UnitProgress | None:
    row = conn.execute("SELECT * FROM unit_progress WHERE unit_id = ?", (unit_id,)).fetchone()
    return _row(row) if row else None


def all_progress(conn: Connection) -> dict[int, UnitProgress]:
    return {row["unit_id"]: _row(row) for row in conn.execute("SELECT * FROM unit_progress")}


def bump_progress(conn: Connection, *, unit_id: int, correct: bool) -> UnitProgress:
    """Count one answered exercise towards the unit's progress."""
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count)"
        " VALUES (?, 'in_progress', 0, 0)"
        " ON CONFLICT(unit_id) DO NOTHING",
        (unit_id,),
    )
    conn.execute(
        "UPDATE unit_progress SET correct_count = correct_count + ?, total_count = total_count + 1"
        " WHERE unit_id = ?",
        (1 if correct else 0, unit_id),
    )
    conn.commit()
    progress = get_progress(conn, unit_id)
    assert progress is not None
    return progress


def complete_unit(conn: Connection, *, unit_id: int) -> UnitProgress:
    completed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO unit_progress (unit_id, status, correct_count, total_count, completed_at)"
        " VALUES (?, 'completed', 0, 0, ?)"
        " ON CONFLICT(unit_id) DO UPDATE SET status = 'completed',"
        " completed_at = excluded.completed_at",
        (unit_id, completed_at),
    )
    conn.commit()
    progress = get_progress(conn, unit_id)
    assert progress is not None
    return progress


def record_attempt(
    conn: Connection, *, unit_id: int, exercise_id: str, correct: bool, answer_json: str
) -> None:
    conn.execute(
        "INSERT INTO exercise_attempts (unit_id, exercise_id, correct, answer_json, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (
            unit_id,
            exercise_id,
            int(correct),
            answer_json,
            dt.datetime.now(dt.timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def attempt_count(conn: Connection, unit_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM exercise_attempts WHERE unit_id = ?", (unit_id,)
    ).fetchone()
    return int(row["n"])


def correct_exercise_ids(conn: Connection, unit_id: int) -> set[str]:
    """Exercise ids of this unit that were answered correctly at least once."""
    rows = conn.execute(
        "SELECT DISTINCT exercise_id FROM exercise_attempts WHERE unit_id = ? AND correct = 1",
        (unit_id,),
    ).fetchall()
    return {row["exercise_id"] for row in rows}
