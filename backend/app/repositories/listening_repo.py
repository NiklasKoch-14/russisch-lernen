from sqlite3 import Connection


def record_run(conn: Connection, *, dialog_id: int, correct: bool, played_at: str) -> None:
    """Vermerken, dass ein Gespräch beantwortet wurde — Grundlage der Auswahl.

    Gezählt wird erst die Antwort, nicht das blosse Anhören: Wiederholen soll
    nichts kosten.
    """
    conn.execute(
        "INSERT INTO listening_runs (dialog_id, correct, played_at) VALUES (?, ?, ?)",
        (dialog_id, int(correct), played_at),
    )
    conn.commit()


def last_played(conn: Connection) -> dict[int, str]:
    """Je Gespräch der jüngste Zeitpunkt."""
    rows = conn.execute(
        "SELECT dialog_id, MAX(played_at) AS played_at FROM listening_runs GROUP BY dialog_id"
    ).fetchall()
    return {row["dialog_id"]: row["played_at"] for row in rows}
