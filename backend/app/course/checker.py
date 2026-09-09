from dataclasses import dataclass

from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    ListenMeaningExercise,
    MatchPairsExercise,
    TokenRef,
    TypeSentenceExercise,
)
from app.content.formkeys import contrast_labels_de
from app.course.lexicon_index import lookup
from app.course.normalize import normalize, words
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    filled_sentence,
    listen_meaning_options,
    match_pairs_sides,
    spoken_text,
)


@dataclass(frozen=True)
class CheckResult:
    correct: bool
    solution_text: str
    solution_translit: str
    explanation_de: str
    trained_forms: list[TokenRef]
    solution_audio: list[str]
    """Die Loesung zum Anhoeren — ein Eintrag je Satz, bei match_pairs je Wort."""


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
        solution_audio=[spoken_text(course, list(exercise.solution))],
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
        solution_audio=[spoken_text(course, filled_sentence(exercise))],
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
        solution_audio=[spoken_text(course, [pair]) for pair in exercise.pairs],
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
        solution_audio=[spoken_text(course, list(correct_option.tokens))],
    )


def _check_listen_meaning(
    course: Course, exercise: ListenMeaningExercise, submission: dict
) -> CheckResult:
    order = listen_meaning_options(course, exercise)
    index = submission.get("option_index")
    original = order[index] if isinstance(index, int) and 0 <= index < len(order) else None
    text, translit = _render(course, list(exercise.sentence))
    correct = original == exercise.correct_index
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=(
            "" if correct else f"Gesagt wurde: {exercise.options_de[exercise.correct_index]}"
        ),
        trained_forms=list(exercise.sentence),
        solution_audio=[spoken_text(course, list(exercise.sentence))],
    )


def _is_typo(typed: str, wanted: str) -> bool:
    """Ein Zeichen daneben — vertippt, verschluckt oder zu viel."""
    if typed == wanted or abs(len(typed) - len(wanted)) > 1:
        return False
    if len(typed) == len(wanted):
        return sum(a != b for a, b in zip(typed, wanted)) == 1
    short, long = sorted((typed, wanted), key=len)
    same = 0
    while same < len(short) and short[same] == long[same]:
        same += 1
    return short[same:] == long[same + 1 :]


def _wanted_count_de(count: int) -> str:
    return "ist ein Wort" if count == 1 else f"sind {count} Wörter"


def _diagnose(course: Course, typed: list[str], solution: list[TokenRef]) -> tuple[str, bool]:
    """Die erste Abweichung benennen. Zweiter Wert: zaehlt sie gegen die Wiederholung?

    Nur eine Meldung, nicht fuenf — wer drei Fehler auf einmal vorgehalten
    bekommt, korrigiert keinen davon.
    """
    count = len(solution)
    if len(typed) < count:
        return f"Da fehlt noch etwas — gesucht {_wanted_count_de(count)}.", True
    if len(typed) > count:
        return f"Ein Wort zu viel — gesucht {_wanted_count_de(count)}.", True

    for word, ref in zip(typed, solution):
        wanted = course.form(ref).text
        if normalize(wanted) == word:
            continue
        found = lookup(course, word)
        same_lexeme = [candidate for candidate in found if candidate[0] == ref[0]]
        if same_lexeme:
            typed_label, wanted_label = contrast_labels_de(same_lexeme[0][1], ref[1])
            return (
                f"Du hast {course.form(same_lexeme[0]).text} geschrieben — das ist "
                f"{typed_label}, hier steht {wanted_label}: {wanted}."
            ), True
        if found:
            return (
                f"{course.form(found[0]).text} heißt {course.gloss(found[0])} — "
                f"gesucht war {wanted}."
            ), True
        # Der Tippfehler kommt erst nach dem Lexikon: рабо́та und рабо́те
        # unterscheiden sich um einen Buchstaben, und genau darum geht es beim
        # Russischlernen. Als Vertipper durchgewinkt waere die Aufgabe wertlos.
        if _is_typo(word, normalize(wanted)):
            return f"Fast — {word} ist verschrieben, richtig ist {wanted}.", False
        return f"Das Wort {word} kommt im Kurs nicht vor.", False

    return "", True


def _check_type_sentence(
    course: Course, exercise: TypeSentenceExercise, submission: dict
) -> CheckResult:
    raw = submission.get("text")
    typed = words(raw) if isinstance(raw, str) else []
    text, translit = _render(course, exercise.solution)
    correct = typed == [normalize(course.form(ref).text) for ref in exercise.solution]
    explanation, counts = ("", True) if correct else _diagnose(course, typed, exercise.solution)
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=explanation,
        # Ein Vertipper oder ein Wort ausserhalb des Kurses sagt nichts darueber,
        # ob die Form sitzt — solche Antworten bleiben aus der Planung heraus.
        trained_forms=list(exercise.solution) if counts else [],
        solution_audio=[spoken_text(course, list(exercise.solution))],
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
    if isinstance(exercise, ListenMeaningExercise):
        return _check_listen_meaning(course, exercise, submission)
    if isinstance(exercise, TypeSentenceExercise):
        return _check_type_sentence(course, exercise, submission)
    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
