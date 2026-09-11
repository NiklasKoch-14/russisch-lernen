import copy

from app.content.loader import load_course
from app.course.checker import check_answer
from app.course.presenter import (
    build_sentence_tiles,
    choose_form_options,
    dialog_reply_options,
    listen_meaning_options,
    match_pairs_sides,
)
from tests.content_factory import MINIMAL_LEXICON, MINIMAL_UNIT, write_course


def _course(tmp_path):
    return load_course(write_course(tmp_path))


def test_build_sentence_accepts_correct_order(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in exercise.solution]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.correct is True
    assert result.solution_text == "я де́лаю"


def test_build_sentence_rejects_wrong_order(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in reversed(exercise.solution)]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.correct is False
    assert result.solution_text == "я де́лаю"


def test_build_sentence_rejects_extra_tile(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    assert check_answer(course, exercise, {"tile_indices": [0, 1, 2]}).correct is False


def _build(course, exercise, refs):
    tiles = build_sentence_tiles(course, exercise)
    return check_answer(course, exercise, {"tile_indices": [tiles.index(ref) for ref in refs]})


def test_build_sentence_names_a_wrong_form(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("ja", "nom"), ("delat", "prs.3sg")])
    assert result.explanation_de == (
        "Du hast де́лает gewählt — das ist die er/sie-Form, hier steht die ich-Form."
    )


def test_build_sentence_names_the_wrong_form_even_in_the_wrong_order(tmp_path):
    # Die falsche Form ist der Lernpunkt; die Reihenfolge wird erst Thema,
    # wenn die Woerter stimmen.
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("delat", "prs.3sg"), ("ja", "nom")])
    assert "das ist die er/sie-Form, hier steht die ich-Form" in result.explanation_de


def test_build_sentence_says_when_only_the_order_is_wrong(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("delat", "prs.1sg"), ("ja", "nom")])
    assert result.explanation_de == "Die Wörter stimmen, nur die Reihenfolge nicht."


def test_build_sentence_says_when_something_is_missing(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("ja", "nom")])
    assert result.explanation_de == "Da fehlt noch etwas — gesucht sind 2 Wörter."


def test_build_sentence_does_not_blame_a_form_that_was_also_chosen_right(tmp_path):
    # де́лаю und де́лает zusammen: die richtige Form ist da, zu viel ist nur die andere.
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("ja", "nom"), ("delat", "prs.1sg"), ("delat", "prs.3sg")])
    assert result.explanation_de == "Ein Wort zu viel — gesucht sind 2 Wörter."


def test_build_sentence_names_a_word_that_does_not_belong(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "ty",
            "lemma": "ты",
            "pos": "pron",
            "gloss_de": "du",
            "forms": {"nom": {"text": "ты", "translit": "ty"}},
        }
    )
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["new_lexemes"] = unit["new_lexemes"] + ["ty"]
    unit["exercises"][0]["distractors"] = [["ty", "nom"]]
    course = load_course(write_course(tmp_path, lexicon=lexicon, units=[unit]))
    exercise = course.units[1].exercises[0]
    result = _build(course, exercise, [("ty", "nom"), ("delat", "prs.1sg")])
    assert result.explanation_de == "ты heißt du und gehört hier nicht hinein."


def test_build_sentence_reports_trained_forms(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    tiles = build_sentence_tiles(course, exercise)
    indices = [tiles.index(ref) for ref in exercise.solution]
    result = check_answer(course, exercise, {"tile_indices": indices})
    assert result.trained_forms == [("ja", "nom"), ("delat", "prs.1sg")]


def test_choose_form_accepts_correct_option(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": options.index(exercise.answer)})
    assert result.correct is True
    assert result.trained_forms == [("delat", "prs.1sg")]


def test_choose_form_wrong_option_names_both_forms(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": options.index(("delat", "prs.3sg"))})
    assert result.correct is False
    assert result.solution_text == "де́лаю"
    assert result.explanation_de == (
        "Du hast де́лает gewählt — das ist die er/sie-Form, hier steht die ich-Form."
    )


def test_choose_form_explanation_leaves_the_solution_to_its_own_line(tmp_path):
    # Das Frontend blendet eine Erklaerung aus, die die Loesung enthaelt — sonst
    # stuende sie doppelt da. Die Formbezeichnung muss also ohne sie auskommen.
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": options.index(("delat", "prs.2sg"))})
    assert result.solution_text not in result.explanation_de


def test_match_pairs_accepts_correct_mapping(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    left, right = match_pairs_sides(course, exercise)
    pairs = [[index, right.index(ref)] for index, ref in enumerate(left)]
    assert check_answer(course, exercise, {"pairs": pairs}).correct is True


def test_match_pairs_rejects_swapped_mapping(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    left, right = match_pairs_sides(course, exercise)
    pairs = [[index, (right.index(ref) + 1) % len(right)] for index, ref in enumerate(left)]
    assert check_answer(course, exercise, {"pairs": pairs}).correct is False


def test_match_pairs_names_the_first_wrong_pair(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    left, right = match_pairs_sides(course, exercise)
    pairs = [[index, (right.index(ref) + 1) % len(right)] for index, ref in enumerate(left)]
    result = check_answer(course, exercise, {"pairs": pairs})
    first = left[0]
    assert result.explanation_de == (
        f"{course.form(first).text} heißt {course.gloss(first)}."
    )


def test_match_pairs_without_a_usable_submission_stays_general(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    result = check_answer(course, exercise, {"pairs": []})
    assert result.explanation_de == "Nicht alle Paare stimmen."


def test_dialog_reply_accepts_correct_option(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[3]
    order = dialog_reply_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": order.index(exercise.correct_index)})
    assert result.correct is True


def test_dialog_reply_wrong_option_returns_its_reason(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[3]
    order = dialog_reply_options(course, exercise)
    wrong = next(i for i, original in enumerate(order) if original != exercise.correct_index)
    result = check_answer(course, exercise, {"option_index": wrong})
    assert result.correct is False
    assert result.explanation_de == "Das ist die Form für er/sie."


def test_out_of_range_index_is_wrong_not_an_error(tmp_path):
    course = _course(tmp_path)
    assert check_answer(course, course.units[1].exercises[1], {"option_index": 99}).correct is False


def test_missing_submission_key_is_wrong_not_an_error(tmp_path):
    course = _course(tmp_path)
    assert check_answer(course, course.units[1].exercises[0], {}).correct is False


LISTEN_MEANING = {
    "id": "1-5",
    "type": "listen_meaning",
    "prompt_de": "Hör zu. Was wird gesagt?",
    "sentence": [["ja", "nom"], ["delat", "prs.1sg"]],
    "correct_index": 0,
    "options_de": ["Ich mache das.", "Er macht das.", "Du machst das."],
}


def _listen_course(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["exercises"].append(LISTEN_MEANING)
    return load_course(write_course(tmp_path, units=[unit]))


def test_listen_meaning_accepts_the_right_option(tmp_path):
    course = _listen_course(tmp_path)
    exercise = course.units[1].exercises[4]
    order = listen_meaning_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": order.index(0)})
    assert result.correct is True
    assert result.trained_forms == [("ja", "nom"), ("delat", "prs.1sg")]
    assert result.solution_text == "я де́лаю"


def test_listen_meaning_rejects_a_wrong_option(tmp_path):
    course = _listen_course(tmp_path)
    exercise = course.units[1].exercises[4]
    order = listen_meaning_options(course, exercise)
    result = check_answer(course, exercise, {"option_index": order.index(2)})
    assert result.correct is False
    assert "Ich mache das." in result.explanation_de


def test_listen_meaning_treats_garbage_as_wrong(tmp_path):
    course = _listen_course(tmp_path)
    exercise = course.units[1].exercises[4]
    assert check_answer(course, exercise, {"option_index": 99}).correct is False
    assert check_answer(course, exercise, {}).correct is False


def test_sentence_exercise_yields_one_audio_part(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[0]
    result = check_answer(course, exercise, {"tile_indices": []})
    assert result.solution_audio == ["я де́лаю"]


def test_match_pairs_yields_one_audio_part_per_word(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[2]
    result = check_answer(course, exercise, {"pairs": []})
    assert result.solution_audio == ["я", "де́лаю"]


def test_solution_audio_uses_speak_as(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "bu_r",
            "lemma": "Р р",
            "pos": "letter",
            "gloss_de": "gerolltes r",
            "forms": {"base": {"text": "Р р", "translit": "r", "speak_as": "ры́ба"}},
        }
    )
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["new_lexemes"] = unit["new_lexemes"] + ["bu_r"]
    unit["exercises"][2]["pairs"] = [["ja", "nom"], ["bu_r", "base"]]
    course = load_course(write_course(tmp_path, lexicon=lexicon, units=[unit]))
    result = check_answer(course, course.units[1].exercises[2], {"pairs": []})
    assert result.solution_audio == ["я", "ры́ба"]
