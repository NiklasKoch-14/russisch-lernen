import datetime as dt
import json
from dataclasses import dataclass
from sqlite3 import Connection

from app.content.models import Course, TokenRef, Unit
from app.course.checker import check_answer
from app.course.presenter import citation_form, present_exercise
from app.repositories import lexeme_srs_repo, progress_repo
from app.repositories.lexeme_srs_repo import SrsState
from app.srs.sm2 import sm2_update


@dataclass(frozen=True)
class AnswerOutcome:
    correct: bool
    solution_text: str
    solution_translit: str
    solution_audio: list[str]
    explanation_de: str
    unit_completed: bool
    correct_count: int
    total_count: int


def _today(today: str | None) -> str:
    return today or dt.date.today().isoformat()


def schedule_form(conn: Connection, ref: TokenRef, *, correct: bool, today: str) -> None:
    """Advance the SM-2 state of a single word form."""
    lexeme_id, form_key = ref
    state = lexeme_srs_repo.get_state(conn, lexeme_id=lexeme_id, form_key=form_key)
    result = sm2_update(
        correct=correct,
        repetitions=state.repetitions if state else 0,
        ease_factor=state.ease_factor if state else 2.5,
        interval_days=state.interval_days if state else 0.0,
    )
    due = dt.date.fromisoformat(today) + dt.timedelta(days=max(result.interval_days, 1))
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=result.interval_days,
            ease_factor=result.ease_factor,
            repetitions=result.repetitions,
            due_date=due.isoformat(),
        ),
    )


def submit_answer(
    conn: Connection,
    course: Course,
    *,
    unit_id: int,
    exercise_id: str,
    submission: dict,
    today: str | None = None,
) -> AnswerOutcome:
    unit = course.units[unit_id]
    exercise = next((item for item in unit.exercises if item.id == exercise_id), None)
    if exercise is None:
        raise KeyError(f"Aufgabe {exercise_id!r} gehört nicht zu Einheit {unit_id}")

    result = check_answer(course, exercise, submission)
    progress_repo.record_attempt(
        conn,
        unit_id=unit_id,
        exercise_id=exercise_id,
        correct=result.correct,
        answer_json=json.dumps(submission, ensure_ascii=False),
    )
    progress = progress_repo.bump_progress(conn, unit_id=unit_id, correct=result.correct)

    day = _today(today)
    for ref in result.trained_forms:
        schedule_form(conn, ref, correct=result.correct, today=day)

    solved = progress_repo.correct_exercise_ids(conn, unit_id)
    completed = solved >= {item.id for item in unit.exercises}
    if completed and progress.status != "completed":
        progress = progress_repo.complete_unit(conn, unit_id=unit_id)

    return AnswerOutcome(
        correct=result.correct,
        solution_text=result.solution_text,
        solution_translit=result.solution_translit,
        solution_audio=result.solution_audio,
        explanation_de=result.explanation_de,
        unit_completed=completed,
        correct_count=progress.correct_count,
        total_count=progress.total_count,
    )


def new_words(course: Course, unit) -> list[dict]:
    """Die neuen Woerter der Einheit mit ihrer Bedeutung.

    Reihenfolge wie in `new_lexemes`, damit der Autor sie steuern kann.
    Unbekannte Kennungen werden uebersprungen statt zu sprengen — der Validator
    meldet sie ohnehin.
    """
    words = []
    for lexeme_id in unit.new_lexemes:
        ref = citation_form(course, lexeme_id)
        if ref is None:
            continue
        form = course.form(ref)
        words.append(
            {
                "id": lexeme_id,
                "text": form.text,
                "translit": form.translit,
                "gloss_de": course.gloss(ref),
            }
        )
    return words


def submit_review_exercise(
    conn: Connection,
    course: Course,
    *,
    unit_id: int,
    exercise_id: str,
    submission: dict,
    today: str | None = None,
) -> AnswerOutcome:
    """Eine Kursaufgabe in der Wiederholung bewerten.

    Bewusst ohne `bump_progress` und `record_attempt`: beide haengen an der
    Einheit, und eine falsch beantwortete Wiederholung darf eine laengst
    abgeschlossene Einheit nicht wieder aufreissen.
    """
    unit = course.units[unit_id]
    exercise = next((item for item in unit.exercises if item.id == exercise_id), None)
    if exercise is None:
        raise KeyError(f"Aufgabe {exercise_id!r} gehört nicht zu Einheit {unit_id}")

    result = check_answer(course, exercise, submission)
    day = _today(today)
    for ref in result.trained_forms:
        schedule_form(conn, ref, correct=result.correct, today=day)

    return AnswerOutcome(
        correct=result.correct,
        solution_text=result.solution_text,
        solution_translit=result.solution_translit,
        solution_audio=result.solution_audio,
        explanation_de=result.explanation_de,
        unit_completed=False,
        correct_count=0,
        total_count=0,
    )


def primer_payload(course: Course, unit: Unit) -> dict | None:
    """Der Grundbegriff vor der Regel — aufgeklappt nur dort, wo er zuerst vorkommt."""
    primer = course.primers.get(unit.grammar_focus.primer or "")
    if primer is None:
        return None
    first_user = min(
        other.id
        for other in course.ordered_units()
        if other.grammar_focus.primer == primer.id
    )
    return {
        "id": primer.id,
        "title_de": primer.title_de,
        "text_de": primer.text_de,
        "first_use": unit.id == first_user,
    }


def unit_payload(course: Course, conn: Connection, unit_id: int) -> dict:
    unit = course.units[unit_id]
    solved = progress_repo.correct_exercise_ids(conn, unit_id)
    return {
        "id": unit.id,
        "stage": unit.stage,
        "title_de": unit.title_de,
        "scenario_de": unit.scenario_de,
        "grammar_focus": {
            "id": unit.grammar_focus.id,
            "title_de": unit.grammar_focus.title_de,
            "explanation_de": unit.grammar_focus.explanation_de,
        },
        "primer": primer_payload(course, unit),
        "new_words": new_words(course, unit),
        "solved_exercise_ids": sorted(solved),
        "exercises": [present_exercise(course, exercise) for exercise in unit.exercises],
    }


def course_overview(course: Course, conn: Connection) -> dict:
    progress = progress_repo.all_progress(conn)
    stages: dict[int, list[dict]] = {}
    for unit in course.ordered_units():
        entry = progress.get(unit.id)
        stages.setdefault(unit.stage, []).append(
            {
                "id": unit.id,
                "title_de": unit.title_de,
                "scenario_de": unit.scenario_de,
                "status": entry.status if entry else "not_started",
                "correct_count": entry.correct_count if entry else 0,
                "exercise_count": len(unit.exercises),
            }
        )
    return {"stages": [{"stage": stage, "units": units} for stage, units in sorted(stages.items())]}
