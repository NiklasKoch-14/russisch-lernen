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


def _due_refs(
    conn: Connection, course: Course, *, today: str, size: int | None
) -> list[TokenRef]:
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
    ordered = [(state.lexeme_id, state.form_key) for state in settled + rest]
    return ordered if size is None else ordered[:size]


def _split_refs(
    conn: Connection,
    course: Course,
    index: ReviewIndex,
    *,
    today: str,
    size: int,
) -> tuple[list[tuple[TokenRef, Location]], list[TokenRef]]:
    """Faellige Formen aufteilen: mit Kontext-Aufgabe und ohne.

    In der Zuordnung steht jede Bedeutung nur einmal. Wiederholt wird je
    Wortform, und ohne diese Regel stuende rechts dreimal „groß" — die Aufgabe
    pruefte dann nur das Wort, nicht die Form. Eine weitere Form mit derselben
    Bedeutung wartet auf eine spaetere Runde; an ihre Stelle rueckt die
    naechste faellige Form.
    """
    allowed = set(progress_repo.all_progress(conn))
    seed = f"review:{today}"

    with_context: list[tuple[TokenRef, Location]] = []
    leftovers: list[TokenRef] = []
    deferred: list[TokenRef] = []
    for ref in _due_refs(conn, course, today=today, size=None):
        if len(with_context) + len(leftovers) == size:
            break
        location = index.pick(ref, allowed_units=allowed, seed=seed)
        if location is not None:
            with_context.append((ref, location))
        elif any(course.gloss(ref) == course.gloss(other) for other in leftovers):
            deferred.append(ref)
        else:
            leftovers.append(ref)

    # Eine Zuordnung mit einem Paar ist keine Aufgabe: dann kommt eine weitere
    # faellige Form dazu, auch wenn sie eine Kontext-Aufgabe haette — aber eine
    # mit anderer Bedeutung.
    if len(leftovers) == 1:
        for position in range(len(with_context) - 1, -1, -1):
            borrowed, _ = with_context[position]
            if course.gloss(borrowed) != course.gloss(leftovers[0]):
                del with_context[position]
                leftovers.append(borrowed)
                break

    # Lieber doppelt als gar nicht: stehen nur noch Formen eines Wortes an,
    # bliebe die Runde sonst leer, obwohl etwas faellig ist.
    if len(leftovers) == 1 and deferred:
        leftovers.append(deferred[0])

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
