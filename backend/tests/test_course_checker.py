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
from tests.content_factory import MINIMAL_UNIT, write_course


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


def test_choose_form_wrong_option_explains_the_right_form(tmp_path):
    course = _course(tmp_path)
    exercise = course.units[1].exercises[1]
    options = choose_form_options(course, exercise)
    wrong = next(index for index, ref in enumerate(options) if ref != exercise.answer)
    result = check_answer(course, exercise, {"option_index": wrong})
    assert result.correct is False
    assert result.solution_text == "де́лаю"
    assert "де́лаю" in result.explanation_de


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
