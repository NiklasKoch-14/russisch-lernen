import copy

from app.content.loader import load_course
from app.content.validator import STAGE_RANGES, validate_course
from tests.content_factory import MINIMAL_LEXICON, MINIMAL_UNIT, write_course

EXTRA_EXERCISES = [dict(MINIMAL_UNIT["exercises"][0], id=f"1-{index}") for index in range(5, 8)]
GOOD_UNIT = dict(MINIMAL_UNIT, exercises=MINIMAL_UNIT["exercises"] + EXTRA_EXERCISES)


def _course(tmp_path, *, lexicon=None, units=None, screening=None):
    return load_course(
        write_course(tmp_path, lexicon=lexicon, units=units or [GOOD_UNIT], screening=screening)
    )


def test_valid_course_has_no_errors(tmp_path):
    assert validate_course(_course(tmp_path)) == []


def test_reports_unknown_lexeme_reference(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["solution"] = [["nope", "nom"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("nope" in error for error in errors)


def test_reports_form_key_missing_from_lexeme(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["solution"] = [["delat", "pst.f"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("pst.f" in error for error in errors)


def test_reports_form_key_not_allowed_for_pos(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][1]["forms"]["nom.sg"] = {"text": "де́ло", "translit": "délo"}
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert any("nom.sg" in error and "verb" in error for error in errors)


def test_reports_missing_stress_mark(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][1]["forms"]["prs.1sg"]["text"] = "делаю"
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert any("Betonung" in error for error in errors)


def test_monosyllabic_form_needs_no_stress_mark(tmp_path):
    assert validate_course(_course(tmp_path)) == []


def test_yo_counts_as_stressed(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "ejo",
            "lemma": "её",
            "pos": "pron",
            "gloss_de": "ihr, sie",
            "forms": {"acc": {"text": "её", "translit": "jejó"}},
        }
    )
    assert validate_course(_course(tmp_path, lexicon=lexicon)) == []


def test_reports_empty_translit_or_gloss(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][0]["gloss_de"] = ""
    lexicon["lexemes"][1]["forms"]["prs.1sg"]["translit"] = ""
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert len(errors) == 2


def test_reports_lexeme_used_before_it_is_introduced(tmp_path):
    first = copy.deepcopy(GOOD_UNIT)
    first["new_lexemes"] = ["ja"]
    errors = validate_course(_course(tmp_path, units=[first]))
    assert any("delat" in error and "eingeführt" in error for error in errors)


def test_lexeme_introduced_earlier_may_be_reused(tmp_path):
    first = copy.deepcopy(GOOD_UNIT)
    second = copy.deepcopy(GOOD_UNIT)
    second["id"] = 2
    second["new_lexemes"] = []
    second["exercises"] = [dict(ex, id=f"2-{i}") for i, ex in enumerate(second["exercises"])]
    assert validate_course(_course(tmp_path, units=[first, second])) == []


def test_reports_distractor_equal_to_solution(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][0]["distractors"] = [["delat", "prs.1sg"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Ablenker" in error for error in errors)


def test_reports_distractor_form_from_other_lexeme_paradigm(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][1]["distractor_forms"] = ["nom"]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("nom" in error and "Paradigma" in error for error in errors)


def test_reports_too_few_exercises(tmp_path):
    unit = copy.deepcopy(MINIMAL_UNIT)
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("mindestens 6" in error for error in errors)


def test_reports_empty_explanation(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["grammar_focus"]["explanation_de"] = "   "
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Erklärung" in error for error in errors)


def test_reports_gap_in_unit_ids(tmp_path):
    third = copy.deepcopy(GOOD_UNIT)
    third["id"] = 3
    third["exercises"] = [dict(ex, id=f"3-{i}") for i, ex in enumerate(third["exercises"])]
    errors = validate_course(_course(tmp_path, units=[GOOD_UNIT, third]))
    assert any("Lücke" in error for error in errors)


def test_reports_stage_mismatch(tmp_path):
    unit = copy.deepcopy(GOOD_UNIT)
    unit["stage"] = 4
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Stufe" in error for error in errors)


def test_reports_screening_probe_pointing_at_missing_unit(tmp_path):
    probes = [
        {"id": "s1", "prompt_de": "?", "options": ["А", "Б"], "correct_index": 0, "maps_to_unit": 99}
    ]
    errors = validate_course(_course(tmp_path, screening=probes))
    assert any("99" in error for error in errors)


def test_stage_ranges_cover_one_to_hundred(tmp_path):
    assert STAGE_RANGES[0] == (1, 4)
    assert STAGE_RANGES[4][1] == 100


def test_reports_match_pairs_with_ambiguous_glosses(tmp_path):
    """Zwei Formen desselben Lexems teilen die Bedeutung — die Aufgabe wäre unlösbar."""
    unit = copy.deepcopy(GOOD_UNIT)
    unit["exercises"][2]["pairs"] = [["delat", "prs.1sg"], ["delat", "prs.3sg"]]
    errors = validate_course(_course(tmp_path, units=[unit]))
    assert any("Bedeutung" in error for error in errors)


def test_match_pairs_with_distinct_glosses_is_fine(tmp_path):
    assert validate_course(_course(tmp_path)) == []


def test_reports_empty_speak_as(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][0]["forms"]["nom"]["speak_as"] = "   "
    errors = validate_course(_course(tmp_path, lexicon=lexicon))
    assert any("speak_as" in error for error in errors)
