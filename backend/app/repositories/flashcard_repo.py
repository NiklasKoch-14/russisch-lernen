from sqlite3 import Connection


def record(conn: Connection, *, lexeme_id: str, correct: bool, answered_at: str) -> None:
    """Eine beantwortete Karte vermerken — Grundlage der Reihenfolge."""
    conn.execute(
        "INSERT INTO flashcard_runs (lexeme_id, correct, answered_at) VALUES (?, ?, ?)",
        (lexeme_id, int(correct), answered_at),
    )
    conn.commit()


def last_answers(conn: Connection) -> dict[str, tuple[str, bool]]:
    """Je Wort die jüngste Antwort: (Zeitpunkt, war sie richtig?).

    Nur die jüngste zählt: wer ein Wort dreimal falsch und danach richtig hatte,
    hat es jetzt gekonnt.
    """
    rows = conn.execute(
        "SELECT lexeme_id, answered_at, correct FROM flashcard_runs"
        " WHERE (lexeme_id, answered_at) IN ("
        "   SELECT lexeme_id, MAX(answered_at) FROM flashcard_runs GROUP BY lexeme_id"
        " )"
    ).fetchall()
    return {row["lexeme_id"]: (row["answered_at"], bool(row["correct"])) for row in rows}
