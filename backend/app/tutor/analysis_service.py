import json
from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo, vocab_repo
from app.repositories.learning_plan_repo import LearningPlan, create_plan
from app.repositories.profile_repo import Profile, update_profile
from app.tutor.prompts import analysis_prompt, learning_plan_prompt


def analyze_session(conn: Connection, *, ollama: OllamaClient, profile: Profile, session_id: int) -> dict:
    turns = session_repo.get_turns(conn, session_id=session_id)
    transcript = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)

    prompt = analysis_prompt(language=profile.language, cefr_level=profile.cefr_level, transcript=transcript)
    response = ollama.chat([{"role": "system", "content": prompt}])
    analysis = _parse_json_object(response)

    new_level = analysis.get("updated_level") or profile.cefr_level
    update_profile(conn, language=profile.language, cefr_level=new_level)

    for suggestion in analysis.get("vocab_suggestions", []):
        vocab_repo.create_card(
            conn,
            language=profile.language,
            term=suggestion["term"],
            translation=suggestion["translation"],
            example_sentence=suggestion.get("example_sentence", ""),
            source_session_id=session_id,
        )

    conn.execute(
        """INSERT INTO session_analyses
           (session_id, updated_level, notable_errors_json, vocab_suggestions_json, next_topics_json, created_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (
            session_id,
            analysis.get("updated_level"),
            json.dumps(analysis.get("notable_errors", [])),
            json.dumps(analysis.get("vocab_suggestions", [])),
            json.dumps(analysis.get("next_topics", [])),
        ),
    )
    conn.commit()

    return analysis


def regenerate_learning_plan(
    conn: Connection, *, ollama: OllamaClient, profile: Profile, notes: str
) -> LearningPlan:
    prompt = learning_plan_prompt(language=profile.language, cefr_level=profile.cefr_level, notes=notes)
    response = ollama.chat([{"role": "system", "content": prompt}])
    data = _parse_json_object(response)
    topics = data.get("topics") or ["General conversation practice"]
    return create_plan(conn, language=profile.language, topics=topics)


def _parse_json_object(response: str) -> dict:
    try:
        data = json.loads(response.strip())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
