"""Hörgespräche: laden und prüfen.

Die wichtigste Regel steht in `test_wort_nach_der_min_unit_ist_ein_fehler` —
ein Gespräch darf kein Wort benutzen, das der Lernende noch nicht hatte.
"""

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.content.loader import load_course
from app.content.validator import validate_course
from tests.content_factory import MINIMAL_UNIT, write_course

ZWEITE_EINHEIT = {
    **deepcopy(MINIMAL_UNIT),
    "id": 2,
    "title_de": "Und du?",
    "new_lexemes": ["ty"],
    "exercises": [
        {
            "id": "2-0",
            "type": "build_sentence",
            "prompt_de": "Du machst das.",
            "solution": [["ty", "nom"], ["delat", "prs.2sg"]],
            "distractors": [["delat", "prs.3sg"]],
        },
        *deepcopy(MINIMAL_UNIT["exercises"]),
    ],
}
for _uebung in ZWEITE_EINHEIT["exercises"][1:]:
    _uebung["id"] = _uebung["id"].replace("1-", "2-")

LEXIKON = {
    "version": 1,
    "lexemes": [
        {
            "id": "ja",
            "lemma": "я",
            "pos": "pron",
            "gloss_de": "ich",
            "forms": {"nom": {"text": "я", "translit": "ja"}},
        },
        {
            "id": "ty",
            "lemma": "ты",
            "pos": "pron",
            "gloss_de": "du",
            "forms": {"nom": {"text": "ты", "translit": "ty"}},
        },
        {
            "id": "delat",
            "lemma": "де́лать",
            "pos": "verb",
            "gloss_de": "machen, tun",
            "forms": {
                "inf": {"text": "де́лать", "translit": "délat'"},
                "prs.1sg": {"text": "де́лаю", "translit": "délaju"},
                "prs.2sg": {"text": "де́лаешь", "translit": "délaješ'"},
                "prs.3sg": {"text": "де́лает", "translit": "délajet"},
            },
        },
    ],
}

GESPRAECH = {
    "id": 1,
    "min_unit": 2,
    "title_de": "Zwei bei der Arbeit",
    "speakers": [
        {"name_ru": "Пётр", "name_de": "Pjotr", "voice": "m"},
        {"name_ru": "На́дя", "name_de": "Nadja", "voice": "f"},
    ],
    "lines": [
        {"speaker": 1, "tokens": [["ty", "nom"], ["delat", "prs.2sg"]],
         "translation_de": "Du machst das."},
        {"speaker": 0, "tokens": [["ja", "nom"], ["delat", "prs.1sg"]],
         "translation_de": "Ich mache das."},
        {"speaker": 1, "tokens": [["delat", "prs.3sg"]], "translation_de": "Er macht das."},
    ],
    "question_de": "Worum ging es?",
    "options_de": ["Um die Arbeit.", "Um das Essen.", "Um die Uhrzeit.", "Um den Weg."],
    "correct_index": 0,
}


def schreibe(tmp_path, dialog: dict | None = None, **aenderungen) -> Path:
    """Einen Kurs mit genau einem Gespräch schreiben — Änderungen darauf."""
    content = write_course(
        tmp_path, lexicon=LEXIKON, units=[deepcopy(MINIMAL_UNIT), deepcopy(ZWEITE_EINHEIT)]
    )
    raw = deepcopy(dialog if dialog is not None else GESPRAECH)
    raw.update(aenderungen)
    (content / "dialogs").mkdir(exist_ok=True)
    (content / "dialogs" / f"{raw['id']:03d}.json").write_text(
        json.dumps(raw, ensure_ascii=False), encoding="utf-8"
    )
    return content


def fehler(tmp_path, **aenderungen) -> list[str]:
    """Nur die Meldungen zu Gesprächen — die Einheiten prüft ein anderer Test."""
    meldungen = validate_course(load_course(schreibe(tmp_path, **aenderungen)))
    return [meldung for meldung in meldungen if "Gespräch" in meldung]


def test_lader_liest_ein_gespraech(tmp_path):
    course = load_course(schreibe(tmp_path))
    dialog = course.dialogs[1]
    assert dialog.min_unit == 2
    assert [speaker.voice for speaker in dialog.speakers] == ["m", "f"]
    assert dialog.lines[0].speaker == 1
    assert dialog.lines[0].tokens == [("ty", "nom"), ("delat", "prs.2sg")]
    assert dialog.lines[0].translation_de == "Du machst das."


def test_ohne_verzeichnis_bleibt_die_sammlung_leer(tmp_path):
    content = write_course(tmp_path, lexicon=LEXIKON)
    assert load_course(content).dialogs == {}


def test_ein_sauberes_gespraech_hat_keine_fehler(tmp_path):
    assert fehler(tmp_path) == []


def test_wort_nach_der_min_unit_ist_ein_fehler(tmp_path):
    # ты kommt erst in Einheit 2 — ein Gespräch ab Einheit 1 darf es nicht benutzen.
    meldungen = fehler(tmp_path, min_unit=1)
    assert any("'ty'" in m and "noch nicht eingeführt" in m for m in meldungen)


def test_unbekanntes_lexem_ist_ein_fehler(tmp_path):
    lines = deepcopy(GESPRAECH["lines"])
    lines[0]["tokens"] = [["gibtsnicht", "nom"]]
    assert any("gibtsnicht" in m for m in fehler(tmp_path, lines=lines))


def test_min_unit_ohne_einheit_ist_ein_fehler(tmp_path):
    assert any("min_unit 99" in m for m in fehler(tmp_path, min_unit=99))


def test_sprecher_ausserhalb_der_liste_ist_ein_fehler(tmp_path):
    lines = deepcopy(GESPRAECH["lines"])
    lines[0]["speaker"] = 5
    assert any("Sprecher 5 gibt es nicht" in m for m in fehler(tmp_path, lines=lines))


def test_ein_stummer_sprecher_ist_ein_fehler(tmp_path):
    lines = [dict(line, speaker=0) for line in deepcopy(GESPRAECH["lines"])]
    assert any("nicht jeder Sprecher kommt vor" in m for m in fehler(tmp_path, lines=lines))


def test_ein_einziger_sprecher_ist_kein_gespraech(tmp_path):
    speakers = [deepcopy(GESPRAECH["speakers"][0])]
    lines = [dict(line, speaker=0) for line in deepcopy(GESPRAECH["lines"])]
    meldungen = fehler(tmp_path, speakers=speakers, lines=lines)
    assert any("zwei oder drei Sprecher" in m for m in meldungen)


def test_unbekannte_stimme_ist_ein_fehler(tmp_path):
    speakers = deepcopy(GESPRAECH["speakers"])
    speakers[0]["voice"] = "x"
    assert any("Stimme 'x'" in m for m in fehler(tmp_path, speakers=speakers))


def test_zwei_zeilen_sind_zu_wenig(tmp_path):
    lines = deepcopy(GESPRAECH["lines"])[:2]
    assert any("mindestens 3 Zeilen" in m for m in fehler(tmp_path, lines=lines))


def test_leere_uebersetzung_ist_ein_fehler(tmp_path):
    lines = deepcopy(GESPRAECH["lines"])
    lines[1]["translation_de"] = "  "
    assert any("translation_de ist leer" in m for m in fehler(tmp_path, lines=lines))


def test_doppelte_option_ist_ein_fehler(tmp_path):
    options = ["Um die Arbeit.", "Um die Arbeit.", "Um die Uhrzeit."]
    assert any("doppelt" in m for m in fehler(tmp_path, options_de=options))


def test_zu_wenige_optionen_sind_ein_fehler(tmp_path):
    assert any("mindestens 3 Optionen" in m for m in fehler(tmp_path, options_de=["a", "b"]))


def test_correct_index_ausserhalb_ist_ein_fehler(tmp_path):
    assert any("correct_index 9" in m for m in fehler(tmp_path, correct_index=9))


def test_luecke_in_den_ids_ist_ein_fehler(tmp_path):
    assert any("Lücke" in m for m in fehler(tmp_path, id=2))


@pytest.mark.parametrize("feld", ["min_unit", "speakers", "lines", "question_de"])
def test_fehlendes_feld_bricht_das_laden_ab(tmp_path, feld):
    from app.content.jsonio import ContentError

    unvollstaendig = {k: v for k, v in deepcopy(GESPRAECH).items() if k != feld}
    with pytest.raises(ContentError):
        load_course(schreibe(tmp_path, dialog=unvollstaendig))
