from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.service import schedule_form
from app.course.shuffle import shuffled_order
from app.repositories import lexeme_srs_repo


def _due_refs(conn: Connection, course: Course, *, today: str, size: int) -> list[TokenRef]:
    """Due word forms that still exist in the lexicon, in a stable order."""
    refs: list[TokenRef] = []
    for state in lexeme_srs_repo.due_states(conn, today=today, limit=size * 3):
        lexeme = course.lexemes.get(state.lexeme_id)
        if lexeme is None or state.form_key not in lexeme.forms:
            continue
        refs.append((state.lexeme_id, state.form_key))
        if len(refs) == size:
            break
    return refs


def build_review_round(conn: Connection, course: Course, *, today: str, size: int = 5) -> dict:
    """One matching round over the forms that are due today."""
    refs = _due_refs(conn, course, today=today, size=size)
    if not refs:
        return {"left": [], "right": []}

    right_order = shuffled_order(f"review:{today}", len(refs))
    left = [
        {
            "index": index,
            "ref": f"{ref[0]}:{ref[1]}",
            "text": course.form(ref).text,
            "translit": course.form(ref).translit,
        }
        for index, ref in enumerate(refs)
    ]
    right = [
        {"index": index, "gloss_de": course.gloss(refs[position])}
        for index, position in enumerate(right_order)
    ]
    return {"left": left, "right": right}


def grade_review_round(
    conn: Connection, course: Course, *, today: str, submission: dict, size: int = 5
) -> dict:
    """Grade a round rebuilt from the same due query, then reschedule each form."""
    refs = _due_refs(conn, course, today=today, size=size)
    right_order = shuffled_order(f"review:{today}", len(refs))
    chosen: dict[int, int] = {}
    for pair in submission.get("pairs", []):
        if (
            isinstance(pair, (list, tuple))
            and len(pair) == 2
            and isinstance(pair[0], int)
            and isinstance(pair[1], int)
            and 0 <= pair[0] < len(refs)
            and 0 <= pair[1] < len(right_order)
        ):
            chosen[pair[0]] = pair[1]

    correct_count = 0
    results = []
    for index, ref in enumerate(refs):
        picked = chosen.get(index)
        correct = picked is not None and right_order[picked] == index
        correct_count += int(correct)
        schedule_form(conn, ref, correct=correct, today=today)
        results.append(
            {
                "ref": f"{ref[0]}:{ref[1]}",
                "correct": correct,
                "gloss_de": course.gloss(ref),
                "text": course.form(ref).text,
            }
        )
    return {"correct_count": correct_count, "total_count": len(refs), "results": results}
