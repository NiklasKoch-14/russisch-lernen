import datetime as dt

from app.repositories import vocab_repo


def test_create_card_defaults_to_due_today(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="This is my house."
    )
    assert card.due_date == dt.date.today().isoformat()
    assert card.repetitions == 0
    assert card.ease_factor == 2.5


def test_get_due_cards_only_returns_cards_due_on_or_before_as_of(conn):
    vocab_repo.create_card(conn, language="english", term="house", translation="Haus", example_sentence="x")
    future_card = vocab_repo.create_card(
        conn, language="english", term="cat", translation="Katze", example_sentence="x"
    )
    vocab_repo.update_srs_state(
        conn, card_id=future_card.id, repetitions=1, ease_factor=2.5, interval_days=30, due_date="2099-01-01"
    )

    due = vocab_repo.get_due_cards(conn, language="english")

    assert [c.term for c in due] == ["house"]


def test_get_card_by_id_returns_none_when_missing(conn):
    assert vocab_repo.get_card_by_id(conn, card_id=999) is None


def test_record_quiz_attempt_inserts_row(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="x"
    )
    vocab_repo.record_quiz_attempt(conn, card_id=card.id, user_answer="Haus", correct=True)
    row = conn.execute("SELECT * FROM quiz_attempts WHERE card_id = ?", (card.id,)).fetchone()
    assert row["correct"] == 1
