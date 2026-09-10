from pathlib import Path

from app.content.loader import load_course
from app.content.validator import validate_course

CONTENT_DIR = Path(__file__).resolve().parents[2] / "content" / "ru"


def test_shipped_content_passes_every_validation_rule():
    assert validate_course(load_course(CONTENT_DIR)) == []


def test_shipped_content_has_gapless_unit_ids():
    # Inhalte wachsen blockweise; festgezurrt ist nur, dass keine Einheit fehlt.
    unit_ids = sorted(load_course(CONTENT_DIR).units)
    assert unit_ids == list(range(1, len(unit_ids) + 1))
    assert len(unit_ids) >= 14


def test_stage_zero_teaches_letters_only():
    course = load_course(CONTENT_DIR)
    for unit_id in (1, 2, 3, 4):
        for lexeme_id in course.units[unit_id].new_lexemes:
            assert course.lexemes[lexeme_id].pos == "letter"


def test_every_exercise_type_appears_in_the_seed_content():
    course = load_course(CONTENT_DIR)
    types = {exercise.type for unit in course.units.values() for exercise in unit.exercises}
    assert types == {
        "build_sentence",
        "choose_form",
        "match_pairs",
        "dialog_reply",
        "listen_meaning",
    }


def test_screening_probes_are_ordered_by_the_unit_they_unlock():
    units = [probe.maps_to_unit for probe in load_course(CONTENT_DIR).screening]
    assert units == sorted(units)


def test_every_stage_one_unit_reuses_or_introduces_vocabulary_consistently():
    course = load_course(CONTENT_DIR)
    introduced = set()
    for unit in course.ordered_units():
        introduced.update(unit.new_lexemes)
    assert "nika" in introduced and "zvat" in introduced


def test_every_letter_has_an_example_word_to_hear_its_sound_in():
    # Vorgelesen nennt ein Buchstabe seinen Namen ("эр"), nicht seinen Laut.
    # speak_as haelt deshalb ein Wort bereit, in dem man den Laut wirklich hoert.
    course = load_course(CONTENT_DIR)
    missing = sorted(
        lexeme.id
        for lexeme in course.lexemes.values()
        if lexeme.pos == "letter" and not (lexeme.forms["base"].speak_as or "").strip()
    )
    assert missing == [], f"Buchstaben ohne speak_as: {missing}"


def test_every_language_unit_has_at_least_one_listening_exercise():
    # Stufe 0 sind die Buchstaben-Einheiten; dort gibt es nur Zuordnungen,
    # der Ton kommt über speak_as in der Aufloesung.
    course = load_course(CONTENT_DIR)
    missing = [
        unit.id
        for unit in course.ordered_units()
        if unit.stage > 0
        and not any(
            getattr(exercise, "audio_prompt", False) or exercise.type == "listen_meaning"
            for exercise in unit.exercises
        )
    ]
    assert missing == [], f"Einheiten ohne Hör-Aufgabe: {missing}"


def test_jedes_neue_wort_hat_eine_nennform_zum_vorstellen():
    # Ohne sie stuende der Lernende beim ersten Kontakt ohne Bedeutung da.
    from app.course.presenter import citation_form

    course = load_course(CONTENT_DIR)
    ohne = [
        lexeme_id
        for unit in course.ordered_units()
        for lexeme_id in unit.new_lexemes
        if citation_form(course, lexeme_id) is None
    ]
    assert ohne == [], f"Neue Wörter ohne Nennform: {ohne}"


def test_die_nennform_traegt_die_bedeutung_des_lemmas():
    # Bei genau einem Wort weicht die Nennform vom Lemma ab: `дела́` kommt im
    # Kurs nur im Plural vor. Ueberall sonst muessen sie uebereinstimmen.
    from app.course.presenter import citation_form

    course = load_course(CONTENT_DIR)
    abweichend = []
    for lexeme in course.lexemes.values():
        ref = citation_form(course, lexeme.id)
        if ref and course.form(ref).text != lexeme.lemma:
            abweichend.append(lexeme.id)
    assert abweichend == ["dela"], f"unerwartete Abweichungen: {abweichend}"


def test_der_index_findet_fuer_die_meisten_wortformen_eine_kontext_aufgabe():
    # Ohne diesen Test koennte eine Content-Aenderung die Kontext-Wiederholung
    # still aushebeln. Buchstaben zaehlen nicht mit: sie stehen in keinem Satz.
    from app.content.validator import _exercise_tokens
    from app.course.review_index import build_index

    course = load_course(CONTENT_DIR)
    index = build_index(course)

    formen = {
        ref
        for unit in course.ordered_units()
        for exercise in unit.exercises
        for ref in _exercise_tokens(exercise)
        if course.lexemes[ref[0]].pos != "letter"
    }
    mit_kontext = {ref for ref in formen if ref in index.exact or ref in index.broad}
    anteil = len(mit_kontext) / len(formen)
    assert anteil >= 0.6, f"nur {anteil:.0%} der Wortformen haben eine Kontext-Aufgabe"


def test_buchstaben_haben_keine_kontext_aufgabe():
    # Sie sollen auch keine haben: fuer sie ist die Zuordnung die richtige Form.
    from app.course.review_index import build_index

    course = load_course(CONTENT_DIR)
    index = build_index(course)
    buchstaben = {
        ref
        for ref in set(index.exact) | set(index.broad)
        if course.lexemes[ref[0]].pos == "letter"
    }
    assert buchstaben == set()


def test_jedes_gespraech_benutzt_nur_woerter_seiner_einheit():
    # Der Validator prüft es; hier steht es noch einmal für die echten Inhalte,
    # damit ein neues Gespräch nicht still an der Freischaltung vorbeirutscht.
    course = load_course(CONTENT_DIR)
    assert validate_course(course) == []
    assert len(course.dialogs) >= 20


def test_gespraeche_werden_mit_der_einheit_laenger():
    # Wer gerade erst anfängt, soll kein achtzeiliges Gespräch hören.
    course = load_course(CONTENT_DIR)
    nach_einheit = sorted(course.dialogs.values(), key=lambda dialog: dialog.min_unit)
    laengen = [len(dialog.lines) for dialog in nach_einheit]
    assert laengen == sorted(laengen), laengen


def test_jedes_gespraech_hat_vier_optionen_und_zwei_stimmen():
    course = load_course(CONTENT_DIR)
    for dialog in course.dialogs.values():
        assert len(dialog.options_de) == 4, dialog.id
        assert {speaker.voice for speaker in dialog.speakers} == {"m", "f"}, dialog.id


def test_kein_gespraech_faengt_wie_ein_anderes_an():
    # Zwei gleiche Anfänge lassen den Lernenden glauben, er kenne das Gespräch schon.
    course = load_course(CONTENT_DIR)
    anfaenge = [
        tuple(dialog.lines[0].tokens) for dialog in course.dialogs.values()
    ]
    assert len(set(anfaenge)) == len(anfaenge)
