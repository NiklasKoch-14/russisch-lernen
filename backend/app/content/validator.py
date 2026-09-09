from app.content.formkeys import POS_VALUES, allowed_form_keys
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    ListenMeaningExercise,
    MatchPairsExercise,
    TokenRef,
    Unit,
)
from app.content.validation import check_token as _check_token

STRESS = "́"
VOWELS = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
MIN_EXERCISES = 6

STAGE_RANGES: dict[int, tuple[int, int]] = {
    0: (1, 4),
    1: (5, 24),
    2: (25, 52),
    3: (53, 78),
    4: (79, 100),
}


def _syllables(text: str) -> int:
    return sum(1 for char in text if char in VOWELS)


def _check_lexicon(course: Course) -> list[str]:
    errors: list[str] = []
    for lexeme in course.lexemes.values():
        if lexeme.pos not in POS_VALUES:
            errors.append(f"Lexem {lexeme.id}: unbekannte Wortart {lexeme.pos!r}")
            continue
        if not lexeme.gloss_de.strip():
            errors.append(f"Lexem {lexeme.id}: gloss_de ist leer")
        allowed = allowed_form_keys(lexeme.pos)
        for key, form in lexeme.forms.items():
            if key not in allowed:
                errors.append(
                    f"Lexem {lexeme.id}: Formschlüssel {key!r} ist für Wortart "
                    f"{lexeme.pos!r} nicht erlaubt"
                )
            if not form.translit.strip():
                errors.append(f"Lexem {lexeme.id}, Form {key}: translit ist leer")
            if form.speak_as is not None and not form.speak_as.strip():
                errors.append(
                    f"Lexem {lexeme.id}, Form {key}: speak_as ist gesetzt, aber leer"
                )
            if lexeme.pos == "letter":
                continue
            if _syllables(form.text) > 1 and STRESS not in form.text and "ё" not in form.text:
                errors.append(f"Lexem {lexeme.id}, Form {key}: Betonung fehlt in {form.text!r}")
            if form.text.count(STRESS) > 1:
                errors.append(
                    f"Lexem {lexeme.id}, Form {key}: mehr als eine Betonung in {form.text!r}"
                )
    return errors


def _exercise_tokens(exercise: Exercise) -> list[TokenRef]:
    if isinstance(exercise, BuildSentenceExercise):
        return exercise.solution + exercise.distractors
    if isinstance(exercise, ChooseFormExercise):
        return [token for token in exercise.sentence if token is not None] + [exercise.answer]
    if isinstance(exercise, MatchPairsExercise):
        return list(exercise.pairs)
    if isinstance(exercise, DialogReplyExercise):
        tokens = list(exercise.tutor_line)
        for option in exercise.options:
            tokens.extend(option.tokens)
        return tokens
    if isinstance(exercise, ListenMeaningExercise):
        return list(exercise.sentence)
    return []


def _check_exercise(course: Course, unit: Unit, exercise: Exercise) -> list[str]:
    where = f"Einheit {unit.id}, Aufgabe {exercise.id}"
    errors: list[str] = []
    for token in _exercise_tokens(exercise):
        errors.extend(_check_token(course, token, where))

    if isinstance(exercise, BuildSentenceExercise):
        overlap = set(exercise.distractors) & set(exercise.solution)
        if overlap:
            errors.append(f"{where}: Ablenker {sorted(overlap)} sind Teil der Lösung")
    if isinstance(exercise, ChooseFormExercise):
        lexeme_id, answer_key = exercise.answer
        lexeme = course.lexemes.get(lexeme_id)
        if answer_key in exercise.distractor_forms:
            errors.append(f"{where}: Ablenker enthält die richtige Form {answer_key!r}")
        if lexeme is not None:
            for key in exercise.distractor_forms:
                if key not in lexeme.forms:
                    errors.append(
                        f"{where}: Ablenkerform {key!r} fehlt im Paradigma von {lexeme_id!r}"
                    )
        if None not in exercise.sentence:
            errors.append(f"{where}: sentence enthält keine Lücke")
    if isinstance(exercise, DialogReplyExercise):
        if not 0 <= exercise.correct_index < len(exercise.options):
            errors.append(
                f"{where}: correct_index {exercise.correct_index} liegt außerhalb der Optionen"
            )
        for index, option in enumerate(exercise.options):
            if index != exercise.correct_index and not option.why_de.strip():
                errors.append(f"{where}: falsche Option {index} hat keine Begründung (why_de)")
    if isinstance(exercise, ListenMeaningExercise):
        if len(exercise.options_de) < 3:
            errors.append(f"{where}: braucht mindestens 3 Optionen in options_de")
        if not 0 <= exercise.correct_index < len(exercise.options_de):
            errors.append(
                f"{where}: correct_index {exercise.correct_index} liegt außerhalb der Optionen"
            )
        cleaned = [option.strip() for option in exercise.options_de]
        if any(not option for option in cleaned):
            errors.append(f"{where}: eine Option in options_de ist leer")
        if len(set(cleaned)) != len(cleaned):
            errors.append(f"{where}: zwei Optionen in options_de sind doppelt")
        if not exercise.sentence:
            errors.append(f"{where}: sentence ist leer")
    if isinstance(exercise, MatchPairsExercise):
        if len(exercise.pairs) < 2:
            errors.append(f"{where}: braucht mindestens 2 Paare")
        glosses = [
            course.gloss(pair) for pair in exercise.pairs if pair[0] in course.lexemes
        ]
        if len(set(glosses)) != len(glosses):
            errors.append(
                f"{where}: zwei Paare teilen sich dieselbe Bedeutung — "
                "die Zuordnung wäre nicht eindeutig"
            )
    return errors


def _check_units(course: Course) -> list[str]:
    errors: list[str] = []
    introduced: set[str] = set()

    for position, unit in enumerate(course.ordered_units(), start=1):
        if unit.id != position:
            errors.append(
                f"Einheiten-IDs haben eine Lücke: erwartet {position}, gefunden {unit.id}"
            )
        low, high = STAGE_RANGES.get(unit.stage, (0, 0))
        if not low <= unit.id <= high:
            errors.append(
                f"Einheit {unit.id}: Stufe {unit.stage} passt nicht zum ID-Bereich {low}-{high}"
            )
        if not unit.grammar_focus.explanation_de.strip():
            errors.append(f"Einheit {unit.id}: Erklärung des Grammatik-Fokus ist leer")
        primer_id = unit.grammar_focus.primer
        if primer_id is not None and primer_id not in course.primers:
            errors.append(f"Einheit {unit.id}: Primer {primer_id!r} gibt es nicht")
        if len(unit.exercises) < MIN_EXERCISES:
            errors.append(
                f"Einheit {unit.id}: braucht mindestens 6 Aufgaben, hat {len(unit.exercises)}"
            )

        for lexeme_id in unit.new_lexemes:
            if lexeme_id not in course.lexemes:
                errors.append(f"Einheit {unit.id}: neues Lexem {lexeme_id!r} fehlt im Lexikon")
        introduced.update(unit.new_lexemes)

        seen_ids: set[str] = set()
        for exercise in unit.exercises:
            if exercise.id in seen_ids:
                errors.append(f"Einheit {unit.id}: Aufgaben-ID {exercise.id!r} kommt doppelt vor")
            seen_ids.add(exercise.id)
            errors.extend(_check_exercise(course, unit, exercise))
            for lexeme_id, _ in _exercise_tokens(exercise):
                if lexeme_id in course.lexemes and lexeme_id not in introduced:
                    errors.append(
                        f"Einheit {unit.id}, Aufgabe {exercise.id}: "
                        f"Lexem {lexeme_id!r} wird benutzt, bevor es eingeführt wurde"
                    )
    return errors


def _check_primers(course: Course) -> list[str]:
    errors: list[str] = []
    for primer in course.primers.values():
        if not primer.title_de.strip():
            errors.append(f"Primer {primer.id}: title_de ist leer")
        if not primer.text_de.strip():
            errors.append(f"Primer {primer.id}: text_de ist leer")
    return errors


def _check_screening(course: Course) -> list[str]:
    errors: list[str] = []
    for probe in course.screening:
        if probe.maps_to_unit not in course.units:
            errors.append(
                f"Screening-Sonde {probe.id}: verweist auf Einheit {probe.maps_to_unit}, "
                "die es nicht gibt"
            )
        if not 0 <= probe.correct_index < len(probe.options):
            errors.append(f"Screening-Sonde {probe.id}: correct_index liegt außerhalb der Optionen")
        if len(probe.options) < 2:
            errors.append(f"Screening-Sonde {probe.id}: braucht mindestens 2 Optionen")
    return errors


def validate_course(course: Course) -> list[str]:
    """Return every content rule violation as a German message; empty means valid."""
    return (
        _check_lexicon(course)
        + _check_primers(course)
        + _check_units(course)
        + _check_screening(course)
    )
