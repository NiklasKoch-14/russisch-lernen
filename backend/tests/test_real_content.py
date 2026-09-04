from pathlib import Path

from app.content.loader import load_course
from app.content.validator import validate_course

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "ru"


def test_shipped_content_passes_every_validation_rule():
    assert validate_course(load_course(CONTENT_DIR)) == []


def test_shipped_content_has_the_seed_units():
    assert sorted(load_course(CONTENT_DIR).units) == list(range(1, 15))


def test_stage_zero_teaches_letters_only():
    course = load_course(CONTENT_DIR)
    for unit_id in (1, 2, 3, 4):
        for lexeme_id in course.units[unit_id].new_lexemes:
            assert course.lexemes[lexeme_id].pos == "letter"


def test_every_exercise_type_appears_in_the_seed_content():
    course = load_course(CONTENT_DIR)
    types = {exercise.type for unit in course.units.values() for exercise in unit.exercises}
    assert types == {"build_sentence", "choose_form", "match_pairs", "dialog_reply"}


def test_screening_probes_are_ordered_by_the_unit_they_unlock():
    units = [probe.maps_to_unit for probe in load_course(CONTENT_DIR).screening]
    assert units == sorted(units)


def test_every_stage_one_unit_reuses_or_introduces_vocabulary_consistently():
    course = load_course(CONTENT_DIR)
    introduced = set()
    for unit in course.ordered_units():
        introduced.update(unit.new_lexemes)
    assert "nika" in introduced and "zvat" in introduced
