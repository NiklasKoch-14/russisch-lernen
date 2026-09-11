import copy

import pytest

from app.content.loader import ContentError, load_course
from app.content.morphology import check_morphology
from tests.content_factory import MINIMAL_LEXICON, write_course


def _course(tmp_path, *extra, **changes):
    """Das Minimal-Lexikon, dazu weitere Lexeme und geänderte Formen von де́лать."""
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    delat = next(item for item in lexicon["lexemes"] if item["id"] == "delat")
    for key, text in changes.items():
        delat["forms"][key.replace("_", ".")]["text"] = text
    lexicon["lexemes"].extend(extra)
    return load_course(write_course(tmp_path, lexicon=lexicon))


def _noun(lexeme_id, lemma, forms, **extra):
    return {
        "id": lexeme_id,
        "lemma": lemma,
        "pos": "noun",
        "gloss_de": lexeme_id,
        "forms": {key: {"text": text, "translit": "x"} for key, text in forms.items()},
        **extra,
    }


def test_richtige_formen_gehen_durch(tmp_path):
    assert check_morphology(_course(tmp_path)) == []


def test_vertauschte_form_nennt_was_sie_ist_und_was_gesucht_waere(tmp_path):
    errors = check_morphology(_course(tmp_path, prs_3sg="де́лаю"))
    assert errors == [
        "Lexem delat, Form prs.3sg: де́лаю ist laut Wörterbuch die ich-Form, "
        "gesucht ist die er/sie-Form — erwartet wäre делает."
    ]


def test_vertippte_form_steht_nicht_im_woerterbuch(tmp_path):
    errors = check_morphology(_course(tmp_path, prs_2sg="де́лаешъ"))
    assert len(errors) == 1
    assert errors[0].startswith("Lexem delat, Form prs.2sg: де́лаешъ steht nicht im Wörterbuch")
    assert '"morph_check": false' in errors[0]


def test_form_eines_anderen_wortes_wird_erkannt(tmp_path):
    errors = check_morphology(_course(tmp_path, prs_1sg="чита́ю"))
    assert errors == [
        "Lexem delat, Form prs.1sg: чита́ю ist laut Wörterbuch keine Form von де́лать "
        "— erwartet wäre делаю."
    ]


def test_mehrzahlwort_mit_eigener_grundform(tmp_path):
    # Das Wörterbuch führt де́ньги unter деньга́ und де́ти unter ребёнок —
    # das Lexikon darf trotzdem die Mehrzahl als Grundform nennen.
    dengi = _noun("dengi", "де́ньги", {"nom.pl": "де́ньги", "acc.pl": "де́ньги"})
    deti = _noun("deti", "де́ти", {"nom.pl": "де́ти", "gen.pl": "дете́й"})
    assert check_morphology(_course(tmp_path, dengi, deti)) == []


def test_fall_und_zahl_werden_geprueft(tmp_path):
    rabota = _noun("rabota", "рабо́та", {"nom.sg": "рабо́та", "prp.sg": "рабо́ту"})
    errors = check_morphology(_course(tmp_path, rabota))
    assert errors == [
        "Lexem rabota, Form prp.sg: рабо́ту ist laut Wörterbuch der Akkusativ Einzahl, "
        "gesucht ist der Präpositiv Einzahl — erwartet wäre работе."
    ]


def test_ausnahme_schaltet_die_pruefung_fuer_ein_lexem_ab(tmp_path):
    name = _noun("mila", "Ми́лка", {"nom.sg": "Ми́лкаа"}, morph_check=False)
    assert check_morphology(_course(tmp_path, name)) == []


def test_wortarten_ohne_formen_bleiben_ungeprueft(tmp_path):
    adverb = {
        "id": "quatsch",
        "lemma": "бла́бла",
        "pos": "adv",
        "gloss_de": "Quatsch",
        "forms": {"base": {"text": "бла́бла", "translit": "blabla"}},
    }
    assert check_morphology(_course(tmp_path, adverb)) == []


def test_mehrwortformen_werden_uebersprungen(tmp_path):
    # „бу́ду де́лать" ist eine Zukunft aus zwei Wörtern; das Wörterbuch kennt nur einzelne.
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    delat = next(item for item in lexicon["lexemes"] if item["id"] == "delat")
    delat["forms"]["fut.1sg"] = {"text": "бу́ду де́лать", "translit": "búdu délat'"}
    assert check_morphology(load_course(write_course(tmp_path, lexicon=lexicon))) == []


def test_morph_check_ist_standardmaessig_an(tmp_path):
    assert _course(tmp_path).lexemes["delat"].morph_check is True


def test_morph_check_muss_ein_wahrheitswert_sein(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"][0]["morph_check"] = "nein"
    with pytest.raises(ContentError, match="morph_check"):
        load_course(write_course(tmp_path, lexicon=lexicon))
