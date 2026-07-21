from unittest.mock import MagicMock

from app.repositories import session_repo
from app.repositories.learning_plan_repo import create_plan
from app.repositories.profile_repo import Profile
from app.tutor.dialog_service import send_practice_turn


def _fake_ollama(reply: str) -> MagicMock:
    client = MagicMock()
    client.chat.return_value = reply
    return client


def test_send_practice_turn_persists_user_and_assistant_turns(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    ollama = _fake_ollama("Hello there!")

    reply = send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Hi!")

    assert reply == "Hello there!"
    session_id = session_repo.get_active_session(conn, language="english", session_type="practice")
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert [(t.role, t.content) for t in turns] == [("user", "Hi!"), ("assistant", "Hello there!")]


def test_send_practice_turn_reuses_active_session(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    ollama = _fake_ollama("First reply")
    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Msg 1")

    ollama.chat.return_value = "Second reply"
    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Msg 2")

    session_id = session_repo.get_active_session(conn, language="english", session_type="practice")
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert len(turns) == 4


def test_send_practice_turn_includes_plan_topic_in_system_prompt(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    create_plan(conn, language="english", topics=["Ordering food", "Small talk"])
    ollama = _fake_ollama("Sure, let's talk about food.")

    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Hi!")

    sent_messages = ollama.chat.call_args.args[0]
    assert "Ordering food" in sent_messages[0]["content"]
