import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class VocabCard:
    id: int
    language: str
    term: str
    translation: str
    example_sentence: str
    interval_days: float
    ease_factor: float
    repetitions: int
    due_date: str


_COLUMNS = (
    "id, language, term, translation, example_sentence, "
    "interval_days, ease_factor, repetitions, due_date"
)


def create_card(
    conn: Connection,
    *,
    language: str,
    term: str,
    translation: str,
    example_sentence: str,
    source_session_id: int | None = None,
) -> VocabCard:
    now = dt.datetime.utcnow()
    due_date = now.date().isoformat()
    created_at = now.isoformat()
    cursor = conn.execute(
        """INSERT INTO vocab_cards
           (language, term, translation, example_sentence, source_session_id,
            interval_days, ease_factor, repetitions, due_date, created_at)
           VALUES (?, ?, ?, ?, ?, 0, 2.5, 0, ?, ?)""",
        (language, term, translation, example_sentence, source_session_id, due_date, created_at),
    )
    conn.commit()
    return VocabCard(
        id=cursor.lastrowid,
        language=language,
        term=term,
        translation=translation,
        example_sentence=example_sentence,
        interval_days=0,
        ease_factor=2.5,
        repetitions=0,
        due_date=due_date,
    )


def get_due_cards(conn: Connection, *, language: str, as_of: str | None = None) -> list[VocabCard]:
    as_of = as_of or dt.date.today().isoformat()
    rows = conn.execute(
        f"""SELECT {_COLUMNS} FROM vocab_cards
           WHERE language = ? AND due_date <= ?
           ORDER BY due_date ASC""",
        (language, as_of),
    ).fetchall()
    return [VocabCard(**dict(row)) for row in rows]


def get_card_by_id(conn: Connection, *, card_id: int) -> VocabCard | None:
    row = conn.execute(f"SELECT {_COLUMNS} FROM vocab_cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        return None
    return VocabCard(**dict(row))


def update_srs_state(
    conn: Connection,
    *,
    card_id: int,
    repetitions: int,
    ease_factor: float,
    interval_days: float,
    due_date: str,
) -> None:
    conn.execute(
        """UPDATE vocab_cards
           SET repetitions = ?, ease_factor = ?, interval_days = ?, due_date = ?
           WHERE id = ?""",
        (repetitions, ease_factor, interval_days, due_date, card_id),
    )
    conn.commit()


def record_quiz_attempt(conn: Connection, *, card_id: int, user_answer: str, correct: bool) -> None:
    conn.execute(
        "INSERT INTO quiz_attempts (card_id, user_answer, correct, created_at) VALUES (?, ?, ?, ?)",
        (card_id, user_answer, int(correct), dt.datetime.utcnow().isoformat()),
    )
    conn.commit()
