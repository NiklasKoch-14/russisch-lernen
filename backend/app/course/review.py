from sqlite3 import Connection

from app.content.models import Course, TokenRef
from app.course.presenter import present_exercise
from app.course.review_index import Location, ReviewIndex
from app.course.service import schedule_form
from app.course.shuffle import shuffled_order
from app.repositories import lexeme_srs_repo, progress_repo, review_repo


WARM_UP = 2
"""So viele gefestigte Formen eroeffnen eine Runde — ein leichter Einstieg."""

SETTLED_DAYS = 6.0
"""Ab diesem Abstand gilt eine Form als gefestigt: SM-2 springt nach dem
zweiten Treffer auf sechs Tage."""


def _due_refs(conn: Connection, course: Course, *, today: str, size: int) -> list[TokenRef]:
    """Faellige Formen in der Reihenfolge, in der ein Lehrer abfragen wuerde.

    Erst bis zu zwei gefestigte Formen zum Aufwaermen — wer mit drei Fehlern
    anfaengt, uebt schlecht weiter. Danach die mit dem kuerzesten Abstand: die
    zuletzt gelernten vergisst man nach einer Pause zuerst, was seit Wochen
    sitzt, uebersteht sie. Deshalb werden alle faelligen Formen gelesen und
    nicht nur die zuerst faelligen.
    """
    states = [
        state
        for state in lexeme_srs_repo.due_states(conn, today=today, limit=None)
        if state.lexeme_id in course.lexemes
        and state.form_key in course.lexemes[state.lexeme_id].forms
    ]
    settled = sorted(
        (state for state in states if state.interval_days >= SETTLED_DAYS),
        key=lambda state: -state.interval_days,
    )[:WARM_UP]
    rest = sorted(
        (state for state in states if state not in settled),
        key=lambda state: state.interval_days,
    )
    return [(state.lexeme_id, state.form_key) for state in settled + rest][:size]


def _split_refs(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    size: int,
) -> tuple[list[tuple[TokenRef, Location]], list[TokenRef]]:
    """Faellige Formen aufteilen: mit Kontext-Aufgabe und ohne."""
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
    seed = f"review:{today}"
    right_order = shuffled_order(seed, len(refs))
    return {
        "kind": "pairs",
        # Kommt mit der Antwort zurueck, zusammen mit den Formen aus `left`:
        # bewertet wird, was auf dem Schirm stand, nicht was jetzt faellig ist.
        "seed": seed,
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


def _shown_refs(course: Course, raw: object) -> list[TokenRef]:
    """Die Formen der Zuordnung, wie der Client sie bekommen hat ("lexem:form")."""
    if not isinstance(raw, list):
        raise ValueError("refs fehlt")
    refs: list[TokenRef] = []
    for item in raw:
        lexeme_id, _, form_key = item.partition(":") if isinstance(item, str) else ("", "", "")
        lexeme = course.lexemes.get(lexeme_id)
        if lexeme is None or form_key not in lexeme.forms:
            raise ValueError(f"Unbekannte Form in der Zuordnung: {item!r}")
        refs.append((lexeme_id, form_key))
    return refs


def grade_review_round(
    conn: Connection,
    course: Course,
    *,
    today: str,
    submission: dict,
) -> dict:
    """Die Zuordnung bewerten — gegen die Formen, die der Client gezeigt bekam.

    Frueher wurde die Runde hier neu berechnet. Die Zuordnung steht aber am
    Ende; bis sie abgeschickt wird, sind die Kursaufgaben davor beantwortet und
    deren Formen nicht mehr faellig. Die Neuberechnung zog dann andere Formen
    nach, und richtig Zugeordnetes zaehlte als falsch. Deshalb schickt der
    Client Formen und Seed zurueck. Faelschen koennte er damit nur seine eigene
    Wiederholungsplanung.
    """
    refs = _shown_refs(course, submission.get("refs"))
    seed = submission.get("seed")
    right_order = shuffled_order(seed if isinstance(seed, str) else f"review:{today}", len(refs))
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
        # Nach Bedeutung, nicht nach Position — wie `_check_match_pairs` in der
        # Einheit. Wiederholt wird je Wortform, also stehen де́лаю und де́лает
        # oft in derselben Zuordnung, und rechts zweimal „machen, tun". Welche
        # der beiden Karten man nimmt, laesst sich nicht unterscheiden.
        correct = picked is not None and (
            course.gloss(refs[right_order[picked]]) == course.gloss(ref)
        )
        correct_count += int(correct)
        schedule_form(conn, ref, correct=correct, today=today)
        review_repo.record_run(
            conn, lexeme_id=ref[0], form_key=ref[1], correct=correct, answered_at=today
        )
        results.append(
            {
                "ref": f"{ref[0]}:{ref[1]}",
                "correct": correct,
                "gloss_de": course.gloss(ref),
                "text": course.form(ref).text,
            }
        )
    return {"correct_count": correct_count, "total_count": len(refs), "results": results}
