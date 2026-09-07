import copy

from app.content.loader import load_course
from app.course.presenter import present_exercise, spoken_text
from app.course.shuffle import shuffled_order
from tests.content_factory import MINIMAL_LEXICON, MINIMAL_UNIT, write_course


def _course(tmp_path):
    return load_course(write_course(tmp_path))


def test_shuffled_order_is_a_permutation():
    assert sorted(shuffled_order("1-1", 5)) == [0, 1, 2, 3, 4]


def test_shuffled_order_is_stable_for_same_seed():
    assert shuffled_order("1-1", 6) == shuffled_order("1-1", 6)


def test_shuffled_order_differs_between_seeds():
    assert shuffled_order("1-1", 8) != shuffled_order("1-2", 8)


def test_build_sentence_payload_has_tiles_without_solution(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[0])
    assert payload["type"] == "build_sentence"
    assert len(payload["tiles"]) == 3
    assert {tile["text"] for tile in payload["tiles"]} == {"я", "де́лаю", "де́лает"}
    assert [tile["index"] for tile in payload["tiles"]] == [0, 1, 2]
    assert "solution" not in payload and "distractors" not in payload


def test_choose_form_payload_marks_the_blank(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[1])
    assert payload["sentence"][0]["text"] == "я"
    assert payload["sentence"][1] is None
    assert len(payload["options"]) == 3
    assert "answer" not in payload


def test_match_pairs_payload_shuffles_sides_independently(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[2])
    assert {item["text"] for item in payload["left"]} == {"я", "де́лаю"}
    assert {item["gloss_de"] for item in payload["right"]} == {"ich", "machen, tun"}


def test_dialog_reply_payload_hides_correct_index(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[3])
    assert payload["tutor_line"][0]["text"] == "де́лаешь"
    assert len(payload["options"]) == 2
    assert "correct_index" not in payload
    assert all("why_de" not in option for option in payload["options"])


def test_spoken_text_prefers_speak_as(tmp_path):
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
    course = load_course(write_course(tmp_path, lexicon=lexicon))
    assert spoken_text(course, [("bu_r", "base")]) == "ры́ба"
    assert spoken_text(course, [("ja", "nom")]) == "я"


def test_build_sentence_with_audio_prompt_speaks_the_solution(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["exercises"][0]["audio_prompt"] = True
    course = load_course(write_course(tmp_path, units=[unit]))
    payload = present_exercise(course, course.units[1].exercises[0])
    assert payload["audio_prompt"] is True
    assert payload["audio_text"] == "я де́лаю"


def test_without_audio_prompt_there_is_no_audio_text(tmp_path):
    course = _course(tmp_path)
    payload = present_exercise(course, course.units[1].exercises[0])
    assert payload["audio_prompt"] is False
    assert "audio_text" not in payload


def test_choose_form_audio_text_fills_the_blank(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["exercises"][1]["audio_prompt"] = True
    course = load_course(write_course(tmp_path, units=[unit]))
    payload = present_exercise(course, course.units[1].exercises[1])
    assert payload["audio_text"] == "я де́лаю"


def test_listen_meaning_shuffles_options_and_hides_the_answer(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["exercises"].append(
        {
            "id": "1-5",
            "type": "listen_meaning",
            "prompt_de": "Hör zu.",
            "sentence": [["ja", "nom"], ["delat", "prs.1sg"]],
            "correct_index": 0,
            "options_de": ["Ich mache das.", "Er macht das.", "Du machst das."],
        }
    )
    course = load_course(write_course(tmp_path, units=[unit]))
    payload = present_exercise(course, course.units[1].exercises[4])
    assert sorted(payload["options_de"]) == ["Du machst das.", "Er macht das.", "Ich mache das."]
    assert "correct_index" not in payload
    assert payload["audio_text"] == "я де́лаю"
    assert [word["text"] for word in payload["sentence"]] == ["я", "де́лаю"]
