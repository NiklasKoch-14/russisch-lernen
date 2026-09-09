import copy

from app.content.loader import load_course
from app.course.lexicon_index import build_index, index_for, lookup
from tests.content_factory import MINIMAL_LEXICON, write_course


def _course(tmp_path, lexicon=None):
    return load_course(write_course(tmp_path, lexicon=lexicon))


def test_index_findet_jede_form(tmp_path):
    index = build_index(_course(tmp_path))
    assert index["делаю"] == [("delat", "prs.1sg")]
    assert index["делает"] == [("delat", "prs.3sg")]
    assert index["я"] == [("ja", "nom")]


def test_index_ist_normalisiert(tmp_path):
    # Im Lexikon steht де́лаю mit Betonungszeichen; getippt wird ohne.
    index = build_index(_course(tmp_path))
    assert "де́лаю" not in index


def test_gleiche_form_mehrfach_wird_gesammelt(tmp_path):
    # рабо́те ist Dativ und Präpositiv — beide muessen auffindbar bleiben,
    # sonst benennt die Fehlermeldung die falsche Form.
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].append(
        {
            "id": "rabota",
            "lemma": "рабо́та",
            "pos": "noun",
            "gender": "f",
            "gloss_de": "Arbeit",
            "forms": {
                "nom.sg": {"text": "рабо́та", "translit": "rabóta"},
                "dat.sg": {"text": "рабо́те", "translit": "rabóte"},
                "prp.sg": {"text": "рабо́те", "translit": "rabóte"},
            },
        }
    )
    index = build_index(_course(tmp_path, lexicon))
    assert index["работе"] == [("rabota", "dat.sg"), ("rabota", "prp.sg")]


def test_lookup_kennt_unbekannte_woerter(tmp_path):
    assert lookup(_course(tmp_path), "ко́шка") == []


def test_lookup_normalisiert_die_anfrage(tmp_path):
    assert lookup(_course(tmp_path), "Де́лаю") == [("delat", "prs.1sg")]


def test_index_wird_je_kurs_nur_einmal_gebaut(tmp_path):
    course = _course(tmp_path)
    assert index_for(course) is index_for(course)


def test_ein_anderer_kurs_bekommt_einen_eigenen_index(tmp_path):
    first = _course(tmp_path / "a")
    second = _course(tmp_path / "b")
    assert index_for(first) is not index_for(second)
