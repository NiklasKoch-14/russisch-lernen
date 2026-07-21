import datetime as dt
from difflib import SequenceMatcher
from sqlite3 import Connection

from app.repositories import vocab_repo
from app.srs.sm2 import sm2_update

CORRECT_THRESHOLD = 0.85


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_answer_correct(user_answer: str, expected_translation: str) -> bool:
    ratio = SequenceMatcher(None, _normalize(user_answer), _normalize(expected_translation)).ratio()
    return ratio >= CORRECT_THRESHOLD


def submit_answer(conn: Connection, *, card: vocab_repo.VocabCard, user_answer: str) -> bool:
    correct = is_answer_correct(user_answer, card.translation)
    result = sm2_update(
        correct=correct,
        repetitions=card.repetitions,
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
    )
    due_date = (dt.date.today() + dt.timedelta(days=result.interval_days)).isoformat()
    vocab_repo.update_srs_state(
        conn,
        card_id=card.id,
        repetitions=result.repetitions,
        ease_factor=result.ease_factor,
        interval_days=result.interval_days,
        due_date=due_date,
    )
    vocab_repo.record_quiz_attempt(conn, card_id=card.id, user_answer=user_answer, correct=correct)
    return correct
