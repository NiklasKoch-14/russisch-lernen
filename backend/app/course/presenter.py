from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    Course,
    DialogReplyExercise,
    Exercise,
    MatchPairsExercise,
    TokenRef,
)
from app.course.shuffle import shuffled_order


def _word(course: Course, ref: TokenRef) -> dict:
    form = course.form(ref)
    return {"text": form.text, "translit": form.translit}


def spoken_text(course: Course, refs: list[TokenRef]) -> str:
    """The sentence as it should be read aloud — speak_as wins over the written form."""
    return " ".join((course.form(ref).speak_as or course.form(ref).text) for ref in refs)


def filled_sentence(exercise: ChooseFormExercise) -> list[TokenRef]:
    """The choose_form sentence with the answer put into the blank."""
    return [exercise.answer if ref is None else ref for ref in exercise.sentence]


def build_sentence_tiles(course: Course, exercise: BuildSentenceExercise) -> list[TokenRef]:
    """The tile pool in the exact order the client will see it."""
    pool = list(exercise.solution) + list(exercise.distractors)
    return [pool[position] for position in shuffled_order(exercise.id, len(pool))]


def choose_form_options(course: Course, exercise: ChooseFormExercise) -> list[TokenRef]:
    lexeme_id, _ = exercise.answer
    pool = [exercise.answer] + [(lexeme_id, key) for key in exercise.distractor_forms]
    return [pool[position] for position in shuffled_order(exercise.id, len(pool))]


def match_pairs_sides(
    course: Course, exercise: MatchPairsExercise
) -> tuple[list[TokenRef], list[TokenRef]]:
    left_order = shuffled_order(exercise.id + ":l", len(exercise.pairs))
    right_order = shuffled_order(exercise.id + ":r", len(exercise.pairs))
    left = [exercise.pairs[position] for position in left_order]
    right = [exercise.pairs[position] for position in right_order]
    return left, right


def dialog_reply_options(course: Course, exercise: DialogReplyExercise) -> list[int]:
    """Original option indices in display order."""
    return shuffled_order(exercise.id, len(exercise.options))


def present_exercise(course: Course, exercise: Exercise) -> dict:
    """Render an exercise for the client. Never includes the solution."""
    base = {"id": exercise.id, "type": exercise.type, "prompt_de": exercise.prompt_de}

    if isinstance(exercise, BuildSentenceExercise):
        tiles = build_sentence_tiles(course, exercise)
        payload = base | {
            "tiles": [{"index": index, **_word(course, ref)} for index, ref in enumerate(tiles)],
            "audio_prompt": exercise.audio_prompt,
        }
        if exercise.audio_prompt:
            payload["audio_text"] = spoken_text(course, list(exercise.solution))
        return payload

    if isinstance(exercise, ChooseFormExercise):
        options = choose_form_options(course, exercise)
        payload = base | {
            "sentence": [None if ref is None else _word(course, ref) for ref in exercise.sentence],
            "options": [
                {"index": index, **_word(course, ref)} for index, ref in enumerate(options)
            ],
            "audio_prompt": exercise.audio_prompt,
        }
        if exercise.audio_prompt:
            payload["audio_text"] = spoken_text(course, filled_sentence(exercise))
        return payload

    if isinstance(exercise, MatchPairsExercise):
        left, right = match_pairs_sides(course, exercise)
        return base | {
            "left": [{"index": index, **_word(course, ref)} for index, ref in enumerate(left)],
            "right": [
                {"index": index, "gloss_de": course.gloss(ref)} for index, ref in enumerate(right)
            ],
        }

    if isinstance(exercise, DialogReplyExercise):
        order = dialog_reply_options(course, exercise)
        options = []
        for display_index, original in enumerate(order):
            tokens = exercise.options[original].tokens
            options.append(
                {
                    "index": display_index,
                    "text": " ".join(course.form(ref).text for ref in tokens),
                    "translit": " ".join(course.form(ref).translit for ref in tokens),
                }
            )
        return base | {
            "tutor_line": [_word(course, ref) for ref in exercise.tutor_line],
            "options": options,
        }

    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
