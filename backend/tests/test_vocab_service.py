from app.repositories import vocab_repo
from app.srs.vocab_service import is_answer_correct, submit_answer


def test_is_answer_correct_exact_match():
    assert is_answer_correct("Haus", "Haus") is True


def test_is_answer_correct_case_and_whitespace_insensitive():
    assert is_answer_correct("  haus  ", "Haus") is True


def test_is_answer_correct_tolerates_small_typo():
    assert is_answer_correct("beautifull", "beautiful") is True


def test_is_answer_correct_rejects_wrong_word():
    assert is_answer_correct("Katze", "Haus") is False


def test_submit_answer_updates_srs_state_and_records_attempt(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="x"
    )

    correct = submit_answer(conn, card=card, user_answer="Haus")

    assert correct is True
    updated = vocab_repo.get_card_by_id(conn, card_id=card.id)
    assert updated.repetitions == 1
    assert updated.interval_days == 1.0
    row = conn.execute("SELECT * FROM quiz_attempts WHERE card_id = ?", (card.id,)).fetchone()
    assert row["correct"] == 1
