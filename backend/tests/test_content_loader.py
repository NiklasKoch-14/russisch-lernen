import copy
import json

import pytest

from app.content.loader import ContentError, load_course
from app.content.models import (
    BuildSentenceExercise,
    ChooseFormExercise,
    DialogReplyExercise,
    MatchPairsExercise,
)
from tests.content_factory import MINIMAL_LEXICON, MINIMAL_UNIT, write_course


def test_loads_lexemes_with_forms(tmp_path):
    course = load_course(write_course(tmp_path))
    assert course.lexemes["delat"].pos == "verb"
    assert course.lexemes["delat"].forms["prs.3sg"].text == "де́лает"
    assert course.lexemes["delat"].aspect == "impf"


def test_loads_units_keyed_by_id(tmp_path):
    course = load_course(write_course(tmp_path))
    assert set(course.units) == {1}
    assert course.units[1].grammar_focus.title_de == "Verbendungen im Präsens"


def test_token_lists_become_tuples(tmp_path):
    exercise = load_course(write_course(tmp_path)).units[1].exercises[0]
    assert isinstance(exercise, BuildSentenceExercise)
    assert exercise.solution == [("ja", "nom"), ("delat", "prs.1sg")]
    assert exercise.distractors == [("delat", "prs.3sg")]


def test_blank_marker_becomes_none(tmp_path):
    exercise = load_course(write_course(tmp_path)).units[1].exercises[1]
    assert isinstance(exercise, ChooseFormExercise)
    assert exercise.sentence == [("ja", "nom"), None]
    assert exercise.answer == ("delat", "prs.1sg")


def test_loads_match_pairs_and_dialog_reply(tmp_path):
    exercises = load_course(write_course(tmp_path)).units[1].exercises
    assert isinstance(exercises[2], MatchPairsExercise)
    assert exercises[2].pairs == [("ja", "nom"), ("delat", "prs.1sg")]
    assert isinstance(exercises[3], DialogReplyExercise)
    assert exercises[3].options[1].why_de.startswith("Das ist die Form")


def test_loads_screening_probes(tmp_path):
    course = load_course(write_course(tmp_path))
    assert course.screening[0].maps_to_unit == 1


def test_units_are_sorted_by_id(tmp_path):
    second = dict(MINIMAL_UNIT, id=2)
    course = load_course(write_course(tmp_path, units=[second, MINIMAL_UNIT]))
    assert [unit.id for unit in course.ordered_units()] == [1, 2]


def test_unknown_exercise_type_raises_content_error(tmp_path):
    broken = dict(MINIMAL_UNIT, exercises=[{"id": "1-1", "type": "sing_a_song"}])
    with pytest.raises(ContentError, match="sing_a_song"):
        load_course(write_course(tmp_path, units=[broken]))


def test_missing_lexicon_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "lexicon.json").unlink()
    with pytest.raises(ContentError, match="lexicon.json"):
        load_course(content)


def test_malformed_json_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "units" / "001.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ContentError, match="001.json"):
        load_course(content)


def test_duplicate_unit_id_raises_content_error(tmp_path):
    content = write_course(tmp_path)
    (content / "units" / "009.json").write_text(json.dumps(MINIMAL_UNIT), encoding="utf-8")
    with pytest.raises(ContentError, match="doppelt"):
        load_course(content)


def test_loads_speak_as_when_present(tmp_path):
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
    assert course.lexemes["bu_r"].forms["base"].speak_as == "ры́ба"


def test_speak_as_is_optional(tmp_path):
    course = load_course(write_course(tmp_path))
    assert course.lexemes["ja"].forms["nom"].speak_as is None


def test_audio_prompt_is_rejected_on_other_exercise_types(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    unit["exercises"][2]["audio_prompt"] = True
    with pytest.raises(ContentError, match="audio_prompt"):
        load_course(write_course(tmp_path, units=[unit]))


def test_audio_prompt_defaults_to_false(tmp_path):
    exercise = load_course(write_course(tmp_path)).units[1].exercises[0]
    assert exercise.audio_prompt is False
