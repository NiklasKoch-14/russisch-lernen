import json
from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo
from app.repositories.profile_repo import update_profile
from app.tutor.prompts import build_chat_messages, placement_system_prompt


def start_placement(conn: Connection, *, ollama: OllamaClient, language: str) -> tuple[int, str]:
    session_id = session_repo.create_session(conn, language=language, session_type="placement")
    system_prompt = placement_system_prompt(language=language)
    first_question = ollama.chat([{"role": "system", "content": system_prompt}])
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=first_question)
    return session_id, first_question


def continue_placement(
    conn: Connection, *, ollama: OllamaClient, session_id: int, language: str, user_answer: str
) -> tuple[bool, str]:
    system_prompt = placement_system_prompt(language=language)
    history = session_repo.get_turns(conn, session_id=session_id)
    messages = build_chat_messages(system_prompt=system_prompt, history=history, user_message=user_answer)

    response = ollama.chat(messages)
    session_repo.add_turn(conn, session_id=session_id, role="user", content=user_answer)

    level = _parse_level(response)
    if level is not None:
        session_repo.add_turn(conn, session_id=session_id, role="assistant", content=response)
        session_repo.end_session(conn, session_id=session_id)
        update_profile(conn, cefr_level=level)
        return True, level

    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=response)
    return False, response


def _parse_level(response: str) -> str | None:
    try:
        data = json.loads(response.strip())
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and "level" in data:
        return str(data["level"])
    return None
