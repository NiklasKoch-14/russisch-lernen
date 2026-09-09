import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection, Row

SELECT_COLUMNS = (
    "language, cefr_level, created_at, show_transliteration, placement_unit, audio_autoplay,"
    " type_in_village"
)


@dataclass
class Profile:
    language: str
    cefr_level: str
    created_at: str
    show_transliteration: bool = True
    placement_unit: int | None = None
    audio_autoplay: bool = True
    type_in_village: bool = True


def _row_to_profile(row: Row) -> Profile:
    return Profile(
        language=row["language"],
        cefr_level=row["cefr_level"],
        created_at=row["created_at"],
        show_transliteration=bool(row["show_transliteration"]),
        placement_unit=row["placement_unit"],
        audio_autoplay=bool(row["audio_autoplay"]),
        type_in_village=bool(row["type_in_village"]),
    )


def get_or_create_profile(conn: Connection, default_language: str) -> Profile:
    row = conn.execute(f"SELECT {SELECT_COLUMNS} FROM profile WHERE id = 1").fetchone()
    if row is not None:
        return _row_to_profile(row)

    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at, show_transliteration,"
        " placement_unit, audio_autoplay, type_in_village) VALUES (1, ?, ?, ?, 1, NULL, 1, 1)",
        (default_language, "UNPLACED", created_at),
    )
    conn.commit()
    return Profile(language=default_language, cefr_level="UNPLACED", created_at=created_at)


def update_profile(
    conn: Connection,
    *,
    language: str | None = None,
    cefr_level: str | None = None,
    show_transliteration: bool | None = None,
    placement_unit: int | None = None,
    audio_autoplay: bool | None = None,
    type_in_village: bool | None = None,
) -> Profile:
    current = get_or_create_profile(conn, default_language=language or "russian")
    new = Profile(
        language=language if language is not None else current.language,
        cefr_level=cefr_level if cefr_level is not None else current.cefr_level,
        created_at=current.created_at,
        show_transliteration=(
            show_transliteration
            if show_transliteration is not None
            else current.show_transliteration
        ),
        placement_unit=placement_unit if placement_unit is not None else current.placement_unit,
        audio_autoplay=(
            audio_autoplay if audio_autoplay is not None else current.audio_autoplay
        ),
        type_in_village=(
            type_in_village if type_in_village is not None else current.type_in_village
        ),
    )
    conn.execute(
        "UPDATE profile SET language = ?, cefr_level = ?, show_transliteration = ?,"
        " placement_unit = ?, audio_autoplay = ?, type_in_village = ? WHERE id = 1",
        (
            new.language,
            new.cefr_level,
            int(new.show_transliteration),
            new.placement_unit,
            int(new.audio_autoplay),
            int(new.type_in_village),
        ),
    )
    conn.commit()
    return new
