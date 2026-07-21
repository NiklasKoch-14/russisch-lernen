from unittest.mock import MagicMock

from app.repositories import session_repo
from app.repositories.profile_repo import get_or_create_profile
from app.tutor.placement_service import continue_placement, start_placement


def test_start_placement_creates_session_and_returns_first_question(conn):
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"

    session_id, question = start_placement(conn, ollama=ollama, language="english")

    assert question == "What is your name?"
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert turns == [session_repo.ConversationTurn(role="assistant", content="What is your name?")]


def test_continue_placement_returns_next_question_when_not_finished(conn):
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"
    session_id, _ = start_placement(conn, ollama=ollama, language="english")

    ollama.chat.return_value = "How old are you?"
    finished, result = continue_placement(
        conn, ollama=ollama, session_id=session_id, language="english", user_answer="Anna"
    )

    assert finished is False
    assert result == "How old are you?"


def test_continue_placement_finalizes_level_when_llm_returns_json(conn):
    get_or_create_profile(conn, default_language="english")
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"
    session_id, _ = start_placement(conn, ollama=ollama, language="english")

    ollama.chat.return_value = '{"level": "B1"}'
    finished, result = continue_placement(
        conn, ollama=ollama, session_id=session_id, language="english", user_answer="Anna, 30 years old"
    )

    assert finished is True
    assert result == "B1"
    profile = get_or_create_profile(conn, default_language="english")
    assert profile.cefr_level == "B1"
