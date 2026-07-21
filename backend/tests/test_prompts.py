from app.repositories.session_repo import ConversationTurn
from app.tutor.prompts import (
    analysis_prompt,
    build_chat_messages,
    learning_plan_prompt,
    placement_system_prompt,
    tutor_system_prompt,
)


def test_tutor_system_prompt_includes_language_and_level():
    prompt = tutor_system_prompt(language="english", cefr_level="B1", plan_topic=None)
    assert "english" in prompt
    assert "B1" in prompt


def test_tutor_system_prompt_includes_plan_topic_when_present():
    prompt = tutor_system_prompt(language="english", cefr_level="B1", plan_topic="Ordering food")
    assert "Ordering food" in prompt


def test_placement_system_prompt_includes_language_and_json_instruction():
    prompt = placement_system_prompt(language="english")
    assert "english" in prompt
    assert '"level"' in prompt


def test_build_chat_messages_orders_system_history_then_user():
    history = [ConversationTurn(role="user", content="Hi"), ConversationTurn(role="assistant", content="Hello")]
    messages = build_chat_messages(system_prompt="SYS", history=history, user_message="Bye")

    assert messages == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Bye"},
    ]


def test_analysis_prompt_includes_transcript_and_level():
    prompt = analysis_prompt(language="english", cefr_level="A2", transcript="user: Hi\nassistant: Hello")
    assert "A2" in prompt
    assert "user: Hi" in prompt
    assert '"vocab_suggestions"' in prompt


def test_learning_plan_prompt_includes_notes():
    prompt = learning_plan_prompt(language="english", cefr_level="A2", notes="struggled with past tense")
    assert "struggled with past tense" in prompt
    assert '"topics"' in prompt
