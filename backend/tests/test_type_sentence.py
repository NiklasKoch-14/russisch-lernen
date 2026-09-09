"""Tippaufgabe: Pruefung und deutsche Fehlerdiagnose."""

import copy

import pytest

from app.content.loader import load_course
from app.content.models import TypeSentenceExercise
from app.course.checker import check_answer
from app.course.presenter import present_exercise
from tests.content_factory import MINIMAL_LEXICON, write_course

EXTRA_LEXEMES = [
    {
        "id": "rabota",
        "lemma": "рабо́та",
        "pos": "noun",
        "gender": "f",
        "gloss_de": "Arbeit",
        "forms": {
            "nom.sg": {"text": "рабо́та", "translit": "rabóta"},
            "nom.pl": {"text": "рабо́ты", "translit": "rabóty"},
            "prp.sg": {"text": "рабо́те", "translit": "rabóte"},
        },
    },
    {
        "id": "chai",
        "lemma": "чай",
        "pos": "noun",
        "gender": "m",
        "gloss_de": "Tee",
        "forms": {"nom.sg": {"text": "чай", "translit": "čaj"}},
    },
    {
        "id": "kofe",
        "lemma": "ко́фе",
        "pos": "noun",
        "gender": "m",
        "gloss_de": "Kaffee",
        "forms": {"nom.sg": {"text": "ко́фе", "translit": "kófe"}},
    },
    {
        "id": "na",
        "lemma": "на",
        "pos": "prep",
        "gloss_de": "auf, an",
        "forms": {"base": {"text": "на", "translit": "na"}},
    },
]


@pytest.fixture
def course(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].extend(EXTRA_LEXEMES)
    return load_course(write_course(tmp_path, lexicon=lexicon))


def _exercise(solution, prompt_de="Sag, dass du auf der Arbeit bist."):
    return TypeSentenceExercise(id="bar-01:seed#0", prompt_de=prompt_de, solution=solution)


AT_WORK = [("ja", "nom"), ("na", "base"), ("rabota", "prp.sg")]


class TestPresenter:
    def test_nutzlast_nennt_nur_auftrag_und_wortzahl(self, course):
        payload = present_exercise(course, _exercise(AT_WORK))
        assert payload == {
            "id": "bar-01:seed#0",
            "type": "type_sentence",
            "prompt_de": "Sag, dass du auf der Arbeit bist.",
            "word_count": 3,
        }

    def test_nutzlast_verraet_die_loesung_nicht(self, course):
        payload = present_exercise(course, _exercise(AT_WORK))
        assert "рабо́те" not in str(payload)


class TestRichtig:
    def test_getippter_satz_stimmt(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́те"})
        assert result.correct is True
        assert result.explanation_de == ""
        assert result.solution_text == "я на рабо́те"

    def test_ohne_betonung_und_klein_geschrieben(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "Я на работе."})
        assert result.correct is True

    def test_richtige_antwort_geht_in_die_wiederholung(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́те"})
        assert result.trained_forms == AT_WORK


class TestDiagnose:
    def test_zu_wenige_woerter(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на"})
        assert result.correct is False
        assert result.explanation_de == "Da fehlt noch etwas — gesucht sind 3 Wörter."

    def test_zu_viele_woerter(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́те чай"})
        assert result.explanation_de == "Ein Wort zu viel — gesucht sind 3 Wörter."

    def test_falsche_form_desselben_wortes(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́та"})
        assert result.correct is False
        assert result.explanation_de == (
            "Du hast рабо́та geschrieben — das ist Nominativ, hier steht Präpositiv: рабо́те."
        )

    def test_falsche_form_nennt_die_zahl_nur_wenn_sie_abweicht(self, course):
        result = check_answer(course, _exercise([("rabota", "nom.sg")]), {"text": "рабо́ты"})
        assert result.explanation_de == (
            "Du hast рабо́ты geschrieben — das ist Mehrzahl, hier steht Einzahl: рабо́та."
        )

    def test_anderes_bekanntes_wort(self, course):
        result = check_answer(course, _exercise([("chai", "nom.sg")]), {"text": "ко́фе"})
        assert result.explanation_de == "ко́фе heißt Kaffee — gesucht war чай."

    def test_tippfehler(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабте"})
        assert result.correct is False
        assert result.explanation_de == "Fast — рабте ist verschrieben, richtig ist рабо́те."

    def test_unbekanntes_wort(self, course):
        result = check_answer(course, _exercise([("chai", "nom.sg")]), {"text": "ко́шка"})
        assert result.explanation_de == "Das Wort кошка kommt im Kurs nicht vor."

    def test_leere_eingabe(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": ""})
        assert result.correct is False
        assert result.explanation_de == "Da fehlt noch etwas — gesucht sind 3 Wörter."

    def test_fehlende_eingabe_ist_kein_serverfehler(self, course):
        result = check_answer(course, _exercise(AT_WORK), {})
        assert result.correct is False

    def test_nur_die_erste_abweichung_wird_gemeldet(self, course):
        # Zwei Fehler auf einmal ueberfordern; der erste reicht.
        result = check_answer(course, _exercise(AT_WORK), {"text": "я чай рабо́та"})
        assert result.explanation_de.startswith("чай heißt Tee")

    def test_formverwechslung_schlaegt_tippfehler(self, course):
        # рабо́та und рабо́те unterscheiden sich um einen Buchstaben. Genau das
        # ist aber der Unterschied, um den es beim Russischlernen geht — als
        # Tippfehler durchgewinkt waere die Aufgabe wertlos.
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́та"})
        assert "verschrieben" not in result.explanation_de


class TestWiederholungsplanung:
    def test_falsche_form_zaehlt(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́та"})
        assert result.trained_forms == AT_WORK

    def test_falsches_wort_zaehlt(self, course):
        result = check_answer(course, _exercise([("chai", "nom.sg")]), {"text": "ко́фе"})
        assert result.trained_forms == [("chai", "nom.sg")]

    def test_fehlendes_wort_zaehlt(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на"})
        assert result.trained_forms == AT_WORK

    def test_tippfehler_zaehlt_nicht(self, course):
        # Wer рабте schreibt, kann die Form. Ihn dafuer in die Wiederholung zu
        # schicken, wuerde die Planung mit Handmotorik vergiften.
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабте"})
        assert result.trained_forms == []

    def test_unbekanntes_wort_zaehlt_nicht(self, course):
        result = check_answer(course, _exercise([("chai", "nom.sg")]), {"text": "ко́шка"})
        assert result.trained_forms == []


class TestStelleDesFehlers:
    def test_richtig_hat_keine_stelle(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́те"})
        assert result.wrong_word_index is None

    def test_falsche_form_nennt_die_stelle(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́та"})
        assert result.wrong_word_index == 2

    def test_erstes_falsches_wort_zaehlt(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я чай рабо́та"})
        assert result.wrong_word_index == 1

    def test_zu_viele_woerter_zeigen_auf_das_ueberzaehlige(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на рабо́те чай"})
        assert result.wrong_word_index == 3

    def test_fehlendes_wort_hat_keine_stelle(self, course):
        result = check_answer(course, _exercise(AT_WORK), {"text": "я на"})
        assert result.wrong_word_index is None

    def test_andere_aufgabentypen_kennen_keine_stelle(self, tmp_path):
        from app.content.loader import load_course
        from tests.content_factory import write_course

        other = load_course(write_course(tmp_path / "kurs"))
        result = check_answer(other, other.units[1].exercises[0], {"tile_indices": []})
        assert result.wrong_word_index is None
