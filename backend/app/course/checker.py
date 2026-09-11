from collections import Counter
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
from app.content.formkeys import contrast_labels_de, with_article_de
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

    wrong_word_index: int | None = None
    """Das beanstandete Wort einer getippten Antwort, damit der Client es
    einfaerben kann. None, wo es kein einzelnes Wort ist — bei allen anderen
    Aufgabentypen und wenn schlicht etwas fehlt."""


def _render(course: Course, refs: list[TokenRef]) -> tuple[str, str]:
    return (
        " ".join(course.form(ref).text for ref in refs),
        " ".join(course.form(ref).translit for ref in refs),
    )


def _wanted_count_de(count: int) -> str:
    return "ist ein Wort" if count == 1 else f"sind {count} Wörter"


def _form_contrast(course: Course, chosen: TokenRef, wanted: TokenRef, verb: str) -> str:
    """„Du hast де́лает gewählt — das ist die er/sie-Form, hier steht die ich-Form"

    Ohne Satzende: die getippte Fassung haengt die gesuchte Form noch an.
    """
    chosen_label, wanted_label = contrast_labels_de(chosen[1], wanted[1])
    return (
        f"Du hast {course.form(chosen).text} {verb} — das ist "
        f"{with_article_de(chosen_label)}, hier steht {with_article_de(wanted_label)}"
    )


def _diagnose_tiles(course: Course, chosen: list[TokenRef], solution: list[TokenRef]) -> str:
    """Den wichtigsten Fehler eines gebauten Satzes benennen.

    Die Reihenfolge der Pruefungen ist Absicht: eine falsche Form ist der
    Lernpunkt und wird zuerst genannt, auch wenn zugleich die Wortstellung
    nicht stimmt. Ueber die Reihenfolge redet die Meldung erst, wenn sonst
    alles passt. Die Loesung selbst nennt sie nie — die steht darunter.
    """
    missing = Counter(solution) - Counter(chosen)
    extra = Counter(chosen) - Counter(solution)

    for wanted in solution:
        if wanted not in missing:
            continue
        # Nur eine Form, die statt der gesuchten dasteht — wer beide gewaehlt
        # hat, hat die richtige ja gefunden und nur eine zu viel.
        for other in chosen:
            if other in extra and other[0] == wanted[0]:
                return f"{_form_contrast(course, other, wanted, 'gewählt')}."

    wanted_lexemes = {ref[0] for ref in solution}
    for other in chosen:
        if other[0] not in wanted_lexemes:
            return (
                f"{course.form(other).text} heißt {course.gloss(other)} "
                "und gehört hier nicht hinein."
            )

    if missing:
        return f"Da fehlt noch etwas — gesucht {_wanted_count_de(len(solution))}."
    if extra:
        surplus = sum(extra.values())
        head = "Ein Wort zu viel" if surplus == 1 else f"{surplus} Wörter zu viel"
        return f"{head} — gesucht {_wanted_count_de(len(solution))}."
    return "Die Wörter stimmen, nur die Reihenfolge nicht."


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
        explanation_de="" if correct else _diagnose_tiles(course, chosen, exercise.solution),
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
    explanation = ""
    if not correct:
        # Die Optionen sind Formen desselben Wortes, also laesst sich immer
        # sagen, was man erwischt hat. Ohne gueltige Wahl bleibt nur der
        # Hinweis — das Frontend blendet ihn aus und zeigt die Loesung allein.
        explanation = (
            f"{_form_contrast(course, chosen, exercise.answer, 'gewählt')}."
            if chosen is not None and chosen[0] == exercise.answer[0]
            else f"Hier passt die Form {text}."
        )
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=explanation,
        trained_forms=[exercise.answer],
        solution_audio=[spoken_text(course, filled_sentence(exercise))],
    )


def _check_match_pairs(
    course: Course, exercise: MatchPairsExercise, submission: dict
) -> CheckResult:
    left, right = match_pairs_sides(course, exercise)
    pairs = submission.get("pairs")
    correct = False
    explanation = "Nicht alle Paare stimmen."
    if (
        isinstance(pairs, list)
        and len(pairs) == len(left)
        and all(
            isinstance(pair, (list, tuple))
            and len(pair) == 2
            and isinstance(pair[0], int)
            and isinstance(pair[1], int)
            and 0 <= pair[0] < len(left)
            and 0 <= pair[1] < len(right)
            for pair in pairs
        )
    ):
        wrong = [
            left[pair[0]]
            for pair in sorted(pairs, key=lambda pair: pair[0])
            if course.gloss(left[pair[0]]) != course.gloss(right[pair[1]])
        ]
        correct = not wrong
        if wrong:
            explanation = f"{course.form(wrong[0]).text} heißt {course.gloss(wrong[0])}."
    text, translit = _render(course, exercise.pairs)
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de="" if correct else explanation,
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


def _diagnose(
    course: Course, typed: list[str], solution: list[TokenRef]
) -> tuple[str, bool, int | None]:
    """Die erste Abweichung benennen: Meldung, zaehlt sie gegen die Wiederholung,
    und das wievielte Wort es war.

    Nur eine Meldung, nicht fuenf — wer drei Fehler auf einmal vorgehalten
    bekommt, korrigiert keinen davon.
    """
    count = len(solution)
    if len(typed) < count:
        return f"Da fehlt noch etwas — gesucht {_wanted_count_de(count)}.", True, None
    if len(typed) > count:
        return f"Ein Wort zu viel — gesucht {_wanted_count_de(count)}.", True, count

    for position, (word, ref) in enumerate(zip(typed, solution)):
        wanted = course.form(ref).text
        if normalize(wanted) == word:
            continue
        found = lookup(course, word)
        same_lexeme = [candidate for candidate in found if candidate[0] == ref[0]]
        if same_lexeme:
            return (
                f"{_form_contrast(course, same_lexeme[0], ref, 'geschrieben')}: {wanted}."
            ), True, position
        if found:
            return (
                f"{course.form(found[0]).text} heißt {course.gloss(found[0])} — "
                f"gesucht war {wanted}."
            ), True, position
        # Der Tippfehler kommt erst nach dem Lexikon: рабо́та und рабо́те
        # unterscheiden sich um einen Buchstaben, und genau darum geht es beim
        # Russischlernen. Als Vertipper durchgewinkt waere die Aufgabe wertlos.
        if _is_typo(word, normalize(wanted)):
            return f"Fast — {word} ist verschrieben, richtig ist {wanted}.", False, position
        return f"Das Wort {word} kommt im Kurs nicht vor.", False, position

    return "", True, None


def _check_type_sentence(
    course: Course, exercise: TypeSentenceExercise, submission: dict
) -> CheckResult:
    raw = submission.get("text")
    typed = words(raw) if isinstance(raw, str) else []
    text, translit = _render(course, exercise.solution)
    correct = typed == [normalize(course.form(ref).text) for ref in exercise.solution]
    explanation, counts, position = (
        ("", True, None) if correct else _diagnose(course, typed, exercise.solution)
    )
    return CheckResult(
        correct=correct,
        solution_text=text,
        solution_translit=translit,
        explanation_de=explanation,
        # Ein Vertipper oder ein Wort ausserhalb des Kurses sagt nichts darueber,
        # ob die Form sitzt — solche Antworten bleiben aus der Planung heraus.
        trained_forms=list(exercise.solution) if counts else [],
        solution_audio=[spoken_text(course, list(exercise.solution))],
        wrong_word_index=position,
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
