from sqlite3 import Connection

# Wo überall Üben Spuren hinterlässt — jede Zeile trägt einen Zeitstempel,
# dessen erste zehn Zeichen das Datum sind.
_SOURCES = (
    ("exercise_attempts", "created_at"),
    ("review_runs", "answered_at"),
    ("listening_runs", "played_at"),
    ("game_scene_runs", "played_at"),
    ("flashcard_runs", "answered_at"),
)


def active_days(conn: Connection) -> set[str]:
    """Alle Tage (JJJJ-MM-TT), an denen irgendetwas geübt wurde."""
    query = " UNION ".join(
        f"SELECT substr({column}, 1, 10) AS day FROM {table}" for table, column in _SOURCES
    )
    return {row["day"] for row in conn.execute(query).fetchall()}
