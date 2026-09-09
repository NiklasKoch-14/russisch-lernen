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
from app.course.shuffle import shuffled_order


def _word(course: Course, ref: TokenRef, *, gloss: bool = False) -> dict:
    """Ein Wort für den Client.

    Die Bedeutung bleibt standardmäßig weg: bei „Paare zuordnen" und beim
    Hörverstehen IST sie die Lösung. Wo sie nur hilft — Kacheln, Satzlücken —,
    wird sie ausdrücklich angefordert; die Kachel deckt sie nach längerem
    Verweilen auf.
    """
    form = course.form(ref)
    word = {"text": form.text, "translit": form.translit}
    if gloss:
        word["gloss_de"] = course.gloss(ref)
    return word


# Wie ein Woerterbuch ein Wort auffuehrt. Die Reihenfolge ist die Suchreihenfolge;
# was fehlt, faellt auf die erste vorhandene Form zurueck — `де́ти` etwa gibt es
# nur im Plural, `есть` nur in der dritten Person.
CITATION_FORMS: dict[str, tuple[str, ...]] = {
    "verb": ("inf", "prs.3sg"),
    "noun": ("nom.sg", "nom.pl"),
    "adj": ("nom.m",),
    "pron": ("nom",),
    "num": ("nom", "nom.m"),
}


def citation_form(course: Course, lexeme_id: str) -> TokenRef | None:
    """Die Form, unter der ein Wort im Woerterbuch stuende."""
    lexeme = course.lexemes.get(lexeme_id)
    if lexeme is None or not lexeme.forms:
        return None
    for key in CITATION_FORMS.get(lexeme.pos, ("base",)):
        if key in lexeme.forms:
            return (lexeme_id, key)
    return (lexeme_id, sorted(lexeme.forms)[0])


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


def listen_meaning_options(course: Course, exercise: ListenMeaningExercise) -> list[int]:
    """Original option indices in display order."""
    return shuffled_order(exercise.id, len(exercise.options_de))


def present_exercise(course: Course, exercise: Exercise) -> dict:
    """Render an exercise for the client. Never includes the solution."""
    base = {"id": exercise.id, "type": exercise.type, "prompt_de": exercise.prompt_de}

    if isinstance(exercise, BuildSentenceExercise):
        tiles = build_sentence_tiles(course, exercise)
        payload = base | {
            "tiles": [
                {"index": index, **_word(course, ref, gloss=True)}
                for index, ref in enumerate(tiles)
            ],
            "audio_prompt": exercise.audio_prompt,
        }
        if exercise.audio_prompt:
            payload["audio_text"] = spoken_text(course, list(exercise.solution))
        return payload

    if isinstance(exercise, ChooseFormExercise):
        options = choose_form_options(course, exercise)
        payload = base | {
            "sentence": [
                None if ref is None else _word(course, ref, gloss=True)
                for ref in exercise.sentence
            ],
            "options": [
                {"index": index, **_word(course, ref, gloss=True)}
                for index, ref in enumerate(options)
            ],
            "audio_prompt": exercise.audio_prompt,
        }
        if exercise.audio_prompt:
            payload["audio_text"] = spoken_text(course, filled_sentence(exercise))
        return payload

    if isinstance(exercise, ListenMeaningExercise):
        order = listen_meaning_options(course, exercise)
        return base | {
            "audio_text": spoken_text(course, list(exercise.sentence)),
            "sentence": [_word(course, ref) for ref in exercise.sentence],
            "options_de": [exercise.options_de[original] for original in order],
        }

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
            "tutor_line": [_word(course, ref, gloss=True) for ref in exercise.tutor_line],
            "options": options,
        }

    if isinstance(exercise, TypeSentenceExercise):
        # Die Wortzahl ist Absicht: die Kachelaufgabe verraet die Satzlaenge
        # ohnehin, und ohne sie raet man beim Auftrag „frag zurueck", ob ein
        # oder vier Woerter gemeint sind.
        return base | {"word_count": len(exercise.solution)}

    raise ValueError(f"Unbekannter Aufgabentyp: {exercise!r}")
