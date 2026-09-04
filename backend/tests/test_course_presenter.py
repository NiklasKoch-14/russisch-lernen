from app.content.loader import load_course
from app.course.presenter import present_exercise
from app.course.shuffle import shuffled_order
from tests.content_factory import write_course


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
