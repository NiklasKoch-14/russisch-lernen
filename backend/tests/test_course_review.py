import copy

import pytest

from app.content.loader import load_course
from app.course import review
from app.course import service as course_service
from app.course.review_index import build_index
from app.repositories import lexeme_srs_repo, progress_repo, review_repo
from app.repositories.lexeme_srs_repo import SrsState
from tests.content_factory import MINIMAL_LEXICON, write_course

TODAY = "2026-09-10"

BUCHSTABEN = [
    {
        "id": "bu_r",
        "lemma": "Р р",
        "pos": "letter",
        "gloss_de": "gerolltes r",
        "forms": {"base": {"text": "Р р", "translit": "r"}},
    },
    {
        "id": "bu_n",
        "lemma": "Н н",
        "pos": "letter",
        "gloss_de": "n wie in nein",
        "forms": {"base": {"text": "Н н", "translit": "n"}},
    },
]


@pytest.fixture
def course(tmp_path):
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    lexicon["lexemes"].extend(BUCHSTABEN)
    return load_course(write_course(tmp_path, lexicon=lexicon))


@pytest.fixture
def index(course):
    return build_index(course)


@pytest.fixture
def gearbeitet(conn):
    """Einheit 1 wurde angefasst — sonst liefert der Index nichts."""
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    return conn


def _due(conn, lexeme_id, form_key, due_date="2026-09-01"):
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=1.0,
            ease_factor=2.5,
            repetitions=1,
            due_date=due_date,
        ),
    )


def _round(conn, course, index):
    return review.build_review_round(conn, course, index, today=TODAY)


def _antwort(zuordnung, pairs):
    """Was der Browser abschickt: Paare, dazu Formen und Seed der gezeigten Runde."""
    return {
        "pairs": pairs,
        "refs": [links["ref"] for links in zuordnung["left"]],
        "seed": zuordnung["seed"],
    }


def test_leere_runde_wenn_nichts_faellig_ist(conn, course, index):
    assert _round(conn, course, index)["items"] == []


def test_faellige_form_kommt_als_kontext_aufgabe(gearbeitet, course, index):
    _due(gearbeitet, "delat", "prs.1sg")
    items = _round(gearbeitet, course, index)["items"]

    aufgaben = [item for item in items if item["kind"] == "exercise"]
    assert len(aufgaben) == 1
    assert aufgaben[0]["unit_id"] == 1
    assert aufgaben[0]["ref"] == "delat:prs.1sg"
    assert aufgaben[0]["type"] == "choose_form"
    assert "options" in aufgaben[0], "die Aufgabe kommt fertig dargestellt"


def test_formen_ohne_kontext_aufgabe_kommen_als_zuordnung(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]

    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1, "hoechstens eine Zuordnung je Runde"
    assert len(zuordnungen[0]["left"]) == 2


def test_eine_einzelne_form_ohne_kontext_bekommt_gesellschaft(gearbeitet, course, index):
    # Eine Zuordnung mit einem Paar ist keine Aufgabe. Ohne Auffuellen fiele die
    # Form Runde fuer Runde durch und wuerde nie wiederholt.
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "delat", "prs.1sg")
    items = _round(gearbeitet, course, index)["items"]

    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen) == 1
    assert len(zuordnungen[0]["left"]) == 2


def test_eine_einzelne_form_ganz_allein_entfaellt(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    assert _round(gearbeitet, course, index)["items"] == []


def test_aufgaben_aus_unbearbeiteten_einheiten_kommen_nicht(conn, course, index):
    # kein bump_progress: Einheit 1 wurde nie angefasst
    _due(conn, "delat", "prs.1sg")
    _due(conn, "ja", "nom")
    items = _round(conn, course, index)["items"]
    assert [item for item in items if item["kind"] == "exercise"] == []


def test_formen_ausserhalb_des_lexikons_werden_uebersprungen(gearbeitet, course, index):
    _due(gearbeitet, "gone", "nom")
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]
    zuordnungen = [item for item in items if item["kind"] == "pairs"]
    assert len(zuordnungen[0]["left"]) == 2


def test_zuordnung_wird_bewertet_und_fortgeschrieben(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    items = _round(gearbeitet, course, index)["items"]
    zuordnung = next(item for item in items if item["kind"] == "pairs")

    pairs = []
    for links in zuordnung["left"]:
        gloss = course.gloss(tuple(links["ref"].split(":", 1)))
        rechts = next(r for r in zuordnung["right"] if r["gloss_de"] == gloss)
        pairs.append([links["index"], rechts["index"]])

    ergebnis = review.grade_review_round(
        gearbeitet, course, today=TODAY, submission=_antwort(zuordnung, pairs)
    )
    assert ergebnis["correct_count"] == 2
    assert lexeme_srs_repo.get_state(gearbeitet, lexeme_id="bu_r", form_key="base").due_date > TODAY


def test_bewertung_sieht_dieselben_formen_wie_die_runde(gearbeitet, course, index):
    # Die Runde zweigt Formen mit Kontext-Aufgabe ab. Wuerde die Bewertung
    # wieder von allen faelligen Formen ausgehen, benotete sie andere.
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    _due(gearbeitet, "delat", "prs.1sg")

    zuordnung = next(
        item for item in _round(gearbeitet, course, index)["items"] if item["kind"] == "pairs"
    )
    ergebnis = review.grade_review_round(
        gearbeitet, course, today=TODAY, submission=_antwort(zuordnung, [])
    )
    assert ergebnis["total_count"] == len(zuordnung["left"])


def _faellig_mit_abstand(conn, lexeme_id, form_key, interval_days):
    lexeme_srs_repo.upsert_state(
        conn,
        SrsState(
            lexeme_id=lexeme_id,
            form_key=form_key,
            interval_days=interval_days,
            ease_factor=2.5,
            repetitions=2,
            due_date="2026-09-01",
        ),
    )


def test_erst_zwei_gefestigte_formen_dann_die_wackligsten(gearbeitet, course):
    # Wer mit drei Fehlern anfaengt, uebt schlecht weiter: zum Aufwaermen zwei
    # Formen, die schon lange sitzen, danach die zuletzt gelernten.
    _faellig_mit_abstand(gearbeitet, "delat", "prs.1sg", 1.0)
    _faellig_mit_abstand(gearbeitet, "delat", "prs.2sg", 10.0)
    _faellig_mit_abstand(gearbeitet, "delat", "prs.3sg", 30.0)
    _faellig_mit_abstand(gearbeitet, "delat", "inf", 2.0)
    _faellig_mit_abstand(gearbeitet, "ja", "nom", 6.0)
    refs = review._due_refs(gearbeitet, course, today=TODAY, size=5)
    assert refs == [
        ("delat", "prs.3sg"),
        ("delat", "prs.2sg"),
        ("delat", "prs.1sg"),
        ("delat", "inf"),
        ("ja", "nom"),
    ]


def test_ohne_gefestigte_formen_gibt_es_kein_aufwaermen(gearbeitet, course):
    _faellig_mit_abstand(gearbeitet, "delat", "prs.2sg", 3.0)
    _faellig_mit_abstand(gearbeitet, "delat", "prs.1sg", 1.0)
    refs = review._due_refs(gearbeitet, course, today=TODAY, size=5)
    assert refs == [("delat", "prs.1sg"), ("delat", "prs.2sg")]


def test_die_wackligsten_kommen_auch_aus_einem_grossen_stapel(conn, tmp_path):
    # Frueher las die Runde nur die zuerst faelligen Formen; eine eben erst
    # gelernte Form haette hinter einem langen Stapel gewartet.
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    for number in range(12):
        lexicon["lexemes"].append(
            {
                "id": f"bu_{number}",
                "lemma": "Н н",
                "pos": "letter",
                "gloss_de": f"Buchstabe {number}",
                "forms": {"base": {"text": "Н н", "translit": "n"}},
            }
        )
    course = load_course(write_course(tmp_path / "gross", lexicon=lexicon))
    for number in range(12):
        lexeme_srs_repo.upsert_state(
            conn,
            SrsState(
                lexeme_id=f"bu_{number}",
                form_key="base",
                interval_days=40.0,
                ease_factor=2.5,
                repetitions=4,
                due_date="2026-08-01",
            ),
        )
    _faellig_mit_abstand(conn, "delat", "prs.1sg", 1.0)
    refs = review._due_refs(conn, course, today=TODAY, size=3)
    assert refs[2] == ("delat", "prs.1sg")


def test_die_bewertete_zuordnung_wird_vermerkt(gearbeitet, course, index):
    _due(gearbeitet, "bu_r", "base")
    _due(gearbeitet, "bu_n", "base")
    zuordnung = next(
        item for item in _round(gearbeitet, course, index)["items"] if item["kind"] == "pairs"
    )
    review.grade_review_round(
        gearbeitet, course, today=TODAY, submission=_antwort(zuordnung, [])
    )
    assert review_repo.count_on(gearbeitet, TODAY) == 2


def test_zuordnung_wird_gegen_die_gezeigten_formen_bewertet(conn, tmp_path):
    # Der Fehler aus dem echten Betrieb: die Zuordnung steht am Ende der Runde.
    # Bis sie abgeschickt wird, sind die Kursaufgaben davor beantwortet und
    # ihre Formen nicht mehr faellig — rechnet die Bewertung die Runde neu aus,
    # rueckt eine andere Form nach, und richtig Zugeordnetes zaehlt als falsch.
    lexicon = copy.deepcopy(MINIMAL_LEXICON)
    for number in range(6):
        lexicon["lexemes"].append(
            {
                "id": f"bu_{number}",
                "lemma": "Н н",
                "pos": "letter",
                "gloss_de": f"Buchstabe {number}",
                "forms": {"base": {"text": f"Н{number}", "translit": "n"}},
            }
        )
    course = load_course(write_course(tmp_path / "echt", lexicon=lexicon))
    index = build_index(course)
    progress_repo.bump_progress(conn, unit_id=1, correct=True)
    _due(conn, "delat", "prs.1sg", due_date="2026-08-01")
    for number in range(6):
        _due(conn, f"bu_{number}", "base")

    items = review.build_review_round(conn, course, index, today=TODAY)["items"]
    kursaufgabe = next(item for item in items if item["kind"] == "exercise")
    zuordnung = next(item for item in items if item["kind"] == "pairs")

    # Erst die Kursaufgabe beantworten — wie im Browser.
    course_service.submit_review_exercise(
        conn,
        course,
        unit_id=kursaufgabe["unit_id"],
        exercise_id=kursaufgabe["exercise_id"],
        submission={"option_index": 0},
        today=TODAY,
    )

    # Dann die Zuordnung richtig loesen, so wie sie auf dem Schirm stand.
    pairs = []
    for links in zuordnung["left"]:
        gloss = course.gloss(tuple(links["ref"].split(":", 1)))
        rechts = next(r for r in zuordnung["right"] if r["gloss_de"] == gloss)
        pairs.append([links["index"], rechts["index"]])
    ergebnis = review.grade_review_round(
        conn, course, today=TODAY, submission=_antwort(zuordnung, pairs)
    )

    assert ergebnis["total_count"] == len(zuordnung["left"])
    assert ergebnis["correct_count"] == len(zuordnung["left"])


def test_eine_unbekannte_form_in_der_antwort_wird_abgelehnt(gearbeitet, course):
    with pytest.raises(ValueError):
        review.grade_review_round(
            gearbeitet,
            course,
            today=TODAY,
            submission={"pairs": [], "refs": ["gibtsnicht:base"], "seed": "s"},
        )


def test_gleiche_bedeutung_zaehlt_auf_jeder_ihrer_karten(conn, course, index):
    # Stehen nur Formen eines Wortes an, landen де́лаю und де́лает doch in
    # derselben Zuordnung, und rechts steht zweimal „machen, tun". Welche der
    # beiden Karten man nimmt, ist nicht zu unterscheiden und darf nicht zaehlen.
    _due(conn, "delat", "prs.1sg")
    _due(conn, "delat", "prs.3sg")
    zuordnung = next(
        item for item in _round(conn, course, index)["items"] if item["kind"] == "pairs"
    )
    glosses = [course.gloss(tuple(links["ref"].split(":", 1))) for links in zuordnung["left"]]
    assert glosses.count("machen, tun") == 2

    # Jede Form bekommt eine Karte mit ihrer Bedeutung — die beiden „machen"
    # aber absichtlich über Kreuz.
    frei = list(reversed(zuordnung["right"]))
    pairs = []
    for links, gloss in zip(zuordnung["left"], glosses):
        rechts = next(r for r in frei if r["gloss_de"] == gloss)
        frei.remove(rechts)
        pairs.append([links["index"], rechts["index"]])

    ergebnis = review.grade_review_round(
        conn, course, today=TODAY, submission=_antwort(zuordnung, pairs)
    )
    assert ergebnis["correct_count"] == 2


def _zuordnung(conn, course, index):
    return next(
        (item for item in _round(conn, course, index)["items"] if item["kind"] == "pairs"), None
    )


def _bedeutungen(course, zuordnung):
    return [course.gloss(tuple(links["ref"].split(":", 1))) for links in zuordnung["left"]]


def test_jede_bedeutung_steht_in_einer_zuordnung_nur_einmal(conn, course, index):
    # Dreimal „groß" rechts prüft nicht, ob man die Form kennt, nur das Wort.
    _due(conn, "delat", "prs.1sg")
    _due(conn, "delat", "prs.3sg")
    _due(conn, "bu_r", "base")
    _due(conn, "bu_n", "base")
    zuordnung = _zuordnung(conn, course, index)
    bedeutungen = _bedeutungen(course, zuordnung)
    assert len(bedeutungen) == len(set(bedeutungen)) == 3
    assert "machen, tun" in bedeutungen


def test_die_zurueckgestellte_form_kommt_in_der_naechsten_runde(conn, course, index):
    _due(conn, "delat", "prs.1sg")
    _due(conn, "delat", "prs.3sg")
    _due(conn, "bu_r", "base")
    erste = _zuordnung(conn, course, index)
    review.grade_review_round(conn, course, today=TODAY, submission=_antwort(erste, []))
    # Die bewerteten Formen sind jetzt fuer morgen geplant; die zurueckgestellte
    # Form von делать ist noch faellig und bekommt ihre eigene Runde.
    verbleibend = [
        (state.lexeme_id, state.form_key)
        for state in lexeme_srs_repo.due_states(conn, today=TODAY, limit=None)
    ]
    assert len(verbleibend) == 1 and verbleibend[0][0] == "delat"


def test_lieber_doppelt_als_gar_nicht(conn, course, index):
    # Stehen nur noch Formen eines einzigen Wortes an, bliebe sonst die Runde
    # leer — und die Startseite schickte zu einem Auffrischen, das nichts zeigt.
    _due(conn, "delat", "prs.1sg")
    _due(conn, "delat", "prs.3sg")
    zuordnung = _zuordnung(conn, course, index)
    assert zuordnung is not None
    assert _bedeutungen(course, zuordnung) == ["machen, tun", "machen, tun"]
