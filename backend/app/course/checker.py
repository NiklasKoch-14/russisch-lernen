from dataclasses import dataclass

from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    MatchPairsExercise,
    TokenRef,
)
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    match_pairs_sides,
)


@dataclass(frozen=True)
class CheckResult:
    correct: bool
    solution_text: str
    solution_translit: str
    explanation_de: str
    trained_forms: list[TokenRef]


def _render(course: Course, refs: list[TokenRef]) -> tuple[str, str]:
    return (
        " ".join(course.form(ref).text for ref in refs),
        " ".join(course.form(ref).translit for ref in refs),
    )


def _check_build_sentence(
    course: Course, exercise: BuildSentenceExercise, submission: dict
) -> CheckResult:
    tiles = build_sentence_tiles(course, exercise)
    indices = submission.get("tile_indices")
    chosen: list[TokenRef] = []
    if isinstance(indices, list) and all(
        isinstance(index, int) and 0 <= index < len(tiles) for index in indices
    ):
        chosen = [tiles[index] for index in indices]
    text, translit = _render(course, exercise.solution)
    correct = chosen == exercise.solution
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else f"Richtig ist: {text}",
        trained_forms=list(exercise.solution),
    )


def _check_choose_form(
    course: Course, exercise: ChooseFormExercise, submission: dict
) -> CheckResult:
    options = choose_form_options(course, exercise)
    index = submission.get("option_index")
    chosen = options[index] if isinstance(index, int) and 0 <= index < len(options) else None
    text, translit = _render(course, [exercise.answer])
    correct = chosen == exercise.answer
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else f"Hier passt die Form {text}.",
        trained_forms=[exercise.answer],
    )


def _check_match_pairs(
    course: Course, exercise: MatchPairsExercise, submission: dict
) -> CheckResult:
    left, right = match_pairs_sides(course, exercise)
    pairs = submission.get("pairs")
    correct = False
    if isinstance(pairs, list) and len(pairs) == len(left):
        correct = all(
            isinstance(pair, (list, tuple))
            and len(pair) == 2
            and isinstance(pair[0], int)
            and isinstance(pair[1], int)
            and 0 <= pair[0] < len(left)
            and 0 <= pair[1] < len(right)
            and course.gloss(left[pair[0]]) == course.gloss(right[pair[1]])
            for pair in pairs
        )
    text, translit = _render(course, exercise.pairs)
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else "Nicht alle Paare stimmen.",
        trained_forms=list(exercise.pairs),
    )


def _check_dialog_reply(
    course: Course, exercise: DialogReplyExercise, submission: dict
) -> CheckResult:
    order = dialog_reply_options(course, exercise)
    index = submission.get("option_index")
    original = order[index] if isinstance(index, int) and 0 <= index < len(order) else None
    correct_option = exercise.options[exercise.correct_index]
    text, translit = _render(course, correct_option.tokens)
    correct = original == exercise.correct_index
    explanation = ""
    if not correct:
        explanation = (
            exercise.options[original].why_de if original is not None else f"Richtig ist: {text}"
        )
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=explanation,
        trained_forms=list(correct_option.tokens),
    )


def check_answer(course: Course, exercise: Exercise, submission: dict) -> CheckResult:
    """Grade a submission. Malformed input counts as a wrong answer, never an error."""
    if isinstance(exercise, BuildSentenceExercise):
        return _check_build_sentence(course, exercise, submission)
    if isinstance(exercise, ChooseFormExercise):
        return _check_choose_form(course, exercise, submission)
    if isinstance(exercise, MatchPairsExercise):
        return _check_match_pairs(course, exercise, submission)
    if isinstance(exercise, DialogReplyExercise):
        return _check_dialog_reply(course, exercise, submission)
    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
