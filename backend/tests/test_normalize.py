from app.course.normalize import normalize, words


def test_betonungszeichen_verschwinden():
    # U+0301 steht im Kurs ueber jedem betonten Vokal; auf einer Tastatur
    # tippt es niemand.
    assert normalize("рабо́те") == "работе"


def test_grossschreibung_spielt_keine_rolle():
    assert normalize("Приве́т") == "привет"


def test_jo_gilt_als_je():
    # Russen tippen ё im Alltag selbst nicht.
    assert normalize("ещё") == "еще"


def test_satzzeichen_verschwinden():
    assert normalize("Приве́т, как дела́?") == "привет как дела"


def test_bindestrich_verschwindet():
    assert normalize("по-ру́сски") == "порусски"


def test_leerraum_wird_zusammengefasst():
    assert normalize("  как   дела́  ") == "как дела"


def test_ziffern_bleiben_stehen():
    assert normalize("сто 10 рубле́й") == "сто 10 рублей"


def test_lateinische_buchstaben_verschwinden():
    # Wer die Tastatur nicht umgestellt hat, tippt sonst unbemerkt Muell.
    assert normalize("privet") == ""


def test_words_zerlegt_den_normalisierten_satz():
    assert words("Приве́т, как дела́?") == ["привет", "как", "дела"]


def test_words_liefert_bei_leerer_eingabe_nichts():
    assert words("   ") == []
