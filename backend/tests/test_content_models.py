import pytest

from app.content.formkeys import POS_VALUES, allowed_form_keys
from app.content.models import Course, Form, Lexeme


def test_verb_form_keys_cover_present_and_past():
    keys = allowed_form_keys("verb")
    assert {"inf", "prs.1sg", "prs.3sg", "pst.f", "imp.sg"} <= keys
    assert "nom.sg" not in keys


def test_noun_form_keys_are_case_number_pairs():
    keys = allowed_form_keys("noun")
    assert {"nom.sg", "acc.sg", "prp.sg", "nom.pl", "ins.pl"} <= keys
    assert len(keys) == 12


def test_invariable_parts_of_speech_only_have_base():
    for pos in ("adv", "prep", "part", "conj", "interj", "letter"):
        assert allowed_form_keys(pos) == frozenset({"base"})


def test_unknown_pos_raises():
    with pytest.raises(KeyError):
        allowed_form_keys("verbb")


def test_pos_values_match_formkey_table():
    assert "verb" in POS_VALUES and "letter" in POS_VALUES


def test_course_lookup_returns_form_text():
    lexeme = Lexeme(
        id="delat",
        lemma="де́лать",
        pos="verb",
        gloss_de="machen, tun",
        forms={"prs.3sg": Form(text="де́лает", translit="délajet")},
    )
    course = Course(language="russian", lexemes={"delat": lexeme}, units={}, screening=[])
    assert course.form(("delat", "prs.3sg")).text == "де́лает"


def test_course_form_raises_for_missing_lexeme():
    course = Course(language="russian", lexemes={}, units={}, screening=[])
    with pytest.raises(KeyError):
        course.form(("nope", "base"))


def test_numerals_may_carry_gender_forms():
    """оди́н/одна́/одно́ und два/две richten sich nach dem Geschlecht."""
    keys = allowed_form_keys("num")
    assert {"nom.m", "nom.f", "nom.n"} <= keys
    assert "nom" in keys
