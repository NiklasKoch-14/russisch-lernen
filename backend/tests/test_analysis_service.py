import json
from unittest.mock import MagicMock

from app.repositories import session_repo, vocab_repo
from app.repositories.profile_repo import Profile, get_or_create_profile
from app.tutor.analysis_service import analyze_session, regenerate_learning_plan


def test_analyze_session_updates_profile_and_creates_vocab_cards(conn):
    get_or_create_profile(conn, default_language="english")
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    session_id = session_repo.create_session(conn, language="english", session_type="practice")
    session_repo.add_turn(conn, session_id=session_id, role="user", content="I go to shop yesterday.")
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content="You mean 'I went to the shop yesterday'.")

    ollama = MagicMock()
    ollama.chat.return_value = json.dumps(
        {
            "updated_level": "B1",
            "notable_errors": ["past tense of 'go'"],
            "vocab_suggestions": [
                {"term": "shop", "translation": "Geschäft", "example_sentence": "I went to the shop."}
            ],
            "next_topics": ["Past tense practice"],
        }
    )

    analysis = analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)

    assert analysis["updated_level"] == "B1"
    updated_profile = get_or_create_profile(conn, default_language="english")
    assert updated_profile.cefr_level == "B1"
    due_cards = vocab_repo.get_due_cards(conn, language="english")
    assert [c.term for c in due_cards] == ["shop"]


def test_analyze_session_handles_malformed_llm_response(conn):
    get_or_create_profile(conn, default_language="english")
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    session_id = session_repo.create_session(conn, language="english", session_type="practice")

    ollama = MagicMock()
    ollama.chat.return_value = "not valid json"

    analysis = analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)

    assert analysis == {}
    unchanged_profile = get_or_create_profile(conn, default_language="english")
    assert unchanged_profile.cefr_level == "A2"


def test_regenerate_learning_plan_creates_plan_from_llm_topics(conn):
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    ollama = MagicMock()
    ollama.chat.return_value = json.dumps({"topics": ["Ordering food", "Asking for directions"]})

    plan = regenerate_learning_plan(conn, ollama=ollama, profile=profile, notes="struggled with past tense")

    assert plan.topics == ["Ordering food", "Asking for directions"]


def test_regenerate_learning_plan_falls_back_when_llm_response_has_no_topics(conn):
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    ollama = MagicMock()
    ollama.chat.return_value = "not valid json"

    plan = regenerate_learning_plan(conn, ollama=ollama, profile=profile, notes="")

    assert plan.topics == ["General conversation practice"]
