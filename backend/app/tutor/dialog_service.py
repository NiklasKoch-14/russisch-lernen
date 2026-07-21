from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo
from app.repositories.learning_plan_repo import get_latest_plan
from app.repositories.profile_repo import Profile
from app.tutor.prompts import build_chat_messages, tutor_system_prompt


def send_practice_turn(
    conn: Connection, *, ollama: OllamaClient, profile: Profile, user_message: str
) -> str:
    session_id = session_repo.get_active_session(
        conn, language=profile.language, session_type="practice"
    )
    if session_id is None:
        session_id = session_repo.create_session(
            conn, language=profile.language, session_type="practice"
        )

    plan = get_latest_plan(conn, language=profile.language)
    plan_topic = plan.topics[0] if plan and plan.topics else None

    system_prompt = tutor_system_prompt(
        language=profile.language, cefr_level=profile.cefr_level, plan_topic=plan_topic
    )
    history = session_repo.get_turns(conn, session_id=session_id)
    messages = build_chat_messages(system_prompt=system_prompt, history=history, user_message=user_message)

    assistant_text = ollama.chat(messages)

    session_repo.add_turn(conn, session_id=session_id, role="user", content=user_message)
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=assistant_text)

    return assistant_text
