import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class Profile:
    language: str
    cefr_level: str
    created_at: str


def get_or_create_profile(conn: Connection, default_language: str) -> Profile:
    row = conn.execute(
        "SELECT language, cefr_level, created_at FROM profile WHERE id = 1"
    ).fetchone()
    if row is not None:
        return Profile(language=row["language"], cefr_level=row["cefr_level"], created_at=row["created_at"])

    created_at = dt.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at) VALUES (1, ?, ?, ?)",
        (default_language, "UNPLACED", created_at),
    )
    conn.commit()
    return Profile(language=default_language, cefr_level="UNPLACED", created_at=created_at)


def update_profile(
    conn: Connection, *, language: str | None = None, cefr_level: str | None = None
) -> Profile:
    current = get_or_create_profile(conn, default_language=language or "english")
    new_language = language if language is not None else current.language
    new_level = cefr_level if cefr_level is not None else current.cefr_level
    conn.execute(
        "UPDATE profile SET language = ?, cefr_level = ? WHERE id = 1",
        (new_language, new_level),
    )
    conn.commit()
    return Profile(language=new_language, cefr_level=new_level, created_at=current.created_at)
