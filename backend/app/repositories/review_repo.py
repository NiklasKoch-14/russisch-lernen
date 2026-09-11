from sqlite3 import Connection


def record_run(
    conn: Connection, *, lexeme_id: str, form_key: str, correct: bool, answered_at: str
) -> None:
    """Vermerken, dass eine Form in der Wiederholung bewertet wurde.

    Die Planung selbst steht in `lexeme_srs`; hier geht es nur um das Wann —
    die Startseite zaehlt daraus, wie viel heute schon aufgefrischt wurde.
    """
    conn.execute(
        "INSERT INTO review_runs (lexeme_id, form_key, correct, answered_at) VALUES (?, ?, ?, ?)",
        (lexeme_id, form_key, int(correct), answered_at),
    )
    conn.commit()


def count_on(conn: Connection, day: str) -> int:
    """Wie viele Formen an diesem Tag bewertet wurden."""
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM review_runs WHERE substr(answered_at, 1, 10) = ?", (day,)
    ).fetchone()
    return int(row["n"])
