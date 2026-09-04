import datetime as dt
import json
from sqlite3 import Connection

from app.content.models import Course
from app.repositories.profile_repo import update_profile

WRONG_STREAK_TO_STOP = 2


def probe_payload(course: Course, index: int) -> dict:
    probe = course.screening[index]
    return {
        "id": probe.id,
        "index": index,
        "total": len(course.screening),
        "prompt_de": probe.prompt_de,
        "options": list(probe.options),
    }


def _is_correct(course: Course, index: int, answer: int) -> bool:
    return index < len(course.screening) and answer == course.screening[index].correct_index


def _should_stop(course: Course, answers: list[int]) -> bool:
    if len(answers) >= len(course.screening):
        return True
    streak = 0
    for index, answer in enumerate(answers):
        streak = 0 if _is_correct(course, index, answer) else streak + 1
        if streak >= WRONG_STREAK_TO_STOP:
            return True
    return False


def placement_unit_for(course: Course, answers: list[int]) -> int:
    """The unit to start at: after the last probe the learner got right."""
    unit = 1
    for index, answer in enumerate(answers):
        if _is_correct(course, index, answer):
            unit = max(unit, course.screening[index].maps_to_unit)
    return unit


def next_step(course: Course, answers: list[int]) -> dict:
    if _should_stop(course, answers):
        return {"finished": True, "placement_unit": placement_unit_for(course, answers)}
    return {"finished": False, "probe": probe_payload(course, len(answers))}


def finish_screening(conn: Connection, course: Course, answers: list[int]) -> int:
    unit = placement_unit_for(course, answers)
    conn.execute(
        "INSERT INTO screening_results (answers_json, placement_unit, created_at) VALUES (?, ?, ?)",
        (json.dumps(answers), unit, dt.datetime.now(dt.timezone.utc).isoformat()),
    )
    conn.commit()
    update_profile(conn, placement_unit=unit)
    return unit
