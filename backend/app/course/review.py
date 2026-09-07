from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.presenter import present_exercise
from app.course.review_index import Location, ReviewIndex
from app.course.service import schedule_form
from app.course.shuffle import shuffled_order
from app.repositories import lexeme_srs_repo, progress_repo


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


def _split_refs(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    size: int,
) -> tuple[list[tuple[TokenRef, Location]], list[TokenRef]]:
    """Faellige Formen aufteilen: mit Kontext-Aufgabe und ohne.

    Runde und Bewertung muessen dieselbe Aufteilung sehen — sonst benotet die
    Bewertung andere Formen, als die Runde gestellt hat. Deshalb liegt sie hier
    an einer Stelle und wird von beiden benutzt.
    """
    allowed = set(progress_repo.all_progress(conn))
    seed = f"review:{today}"

    with_context: list[tuple[TokenRef, Location]] = []
    leftovers: list[TokenRef] = []
    for ref in _due_refs(conn, course, today=today, size=size):
        location = index.pick(ref, allowed_units=allowed, seed=seed)
        if location is None:
            leftovers.append(ref)
        else:
            with_context.append((ref, location))

    # Eine Zuordnung mit einem Paar ist keine Aufgabe: dann kommt eine weitere
    # faellige Form dazu, auch wenn sie eine Kontext-Aufgabe haette.
    if len(leftovers) == 1 and with_context:
        borrowed, _ = with_context.pop()
        leftovers.append(borrowed)

    if len(leftovers) < 2:
        leftovers = []

    return with_context, leftovers


def _pairs_item(course: Course, refs: list[TokenRef], *, today: str) -> dict:
    right_order = shuffled_order(f"review:{today}", len(refs))
    return {
        "kind": "pairs",
        "left": [
            {
                "index": index,
                "ref": f"{ref[0]}:{ref[1]}",
                "text": course.form(ref).text,
                "translit": course.form(ref).translit,
            }
            for index, ref in enumerate(refs)
        ],
        "right": [
            {"index": index, "gloss_de": course.gloss(refs[position])}
            for index, position in enumerate(right_order)
        ],
    }


def build_review_round(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    size: int = 5,
) -> dict:
    """Faellige Formen, wo moeglich in einer echten Kursaufgabe."""
    with_context, leftovers = _split_refs(conn, course, index, today=today, size=size)

    items: list[dict] = []
    for ref, (unit_id, exercise_id) in with_context:
        exercise = next(
            item for item in course.units[unit_id].exercises if item.id == exercise_id
        )
        items.append(
            {
                "kind": "exercise",
                "unit_id": unit_id,
                "exercise_id": exercise_id,
                "ref": f"{ref[0]}:{ref[1]}",
                **present_exercise(course, exercise),
            }
        )

    if leftovers:
        items.append(_pairs_item(course, leftovers, today=today))

    return {"items": items}


def grade_review_round(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    submission: dict,
    size: int = 5,
) -> dict:
    """Die Zuordnung bewerten — aus derselben Aufteilung wie die Runde."""
    _, refs = _split_refs(conn, course, index, today=today, size=size)
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
