import os
import time

from app.audio.cache import AudioCache, audio_key, strip_stress


def test_schluessel_ist_stabil_und_inhaltsbestimmt():
    a = audio_key("дом", voice="ru_RU-dmitri-medium", length_scale=1.0)
    b = audio_key("дом", voice="ru_RU-dmitri-medium", length_scale=1.0)
    assert a == b and len(a) == 64


def test_andere_stimme_ergibt_anderen_schluessel():
    a = audio_key("дом", voice="ru_RU-dmitri-medium", length_scale=1.0)
    b = audio_key("дом", voice="ru_RU-irina-medium", length_scale=1.0)
    assert a != b


def test_anderes_tempo_ergibt_anderen_schluessel():
    a = audio_key("дом", voice="ru_RU-dmitri-medium", length_scale=1.0)
    b = audio_key("дом", voice="ru_RU-dmitri-medium", length_scale=1.4)
    assert a != b


def test_strip_stress_entfernt_das_akut_und_laesst_jo_stehen():
    assert strip_stress("де́лаю") == "делаю"
    assert strip_stress("ещё") == "ещё"
    assert strip_stress("дом") == "дом"


def test_ablegen_und_wiederholen(tmp_path):
    cache = AudioCache(tmp_path, max_mb=1)
    assert cache.get("abc") is None
    cache.put("abc", b"RIFFdaten")
    assert cache.get("abc") == b"RIFFdaten"


def test_deckel_verdraengt_bis_die_grenze_haelt(tmp_path):
    cache = AudioCache(tmp_path, max_mb=1)
    block = b"x" * 400_000
    for key in ("a", "b", "c"):
        cache.put(key, block)
        time.sleep(0.01)
    assert cache.total_bytes() <= 1_048_576
    assert cache.get("a") is None
    assert cache.get("c") == block


def test_verdraengt_das_am_laengsten_ungenutzte_nicht_das_aelteste(tmp_path):
    # Genau die Falle: die Saetze aus Einheit 1 sind die aeltesten, kommen in der
    # Wiederholung aber staendig dran. Ohne Auffrischen flogen sie zuerst.
    cache = AudioCache(tmp_path, max_mb=1)
    block = b"x" * 400_000
    cache.put("alt", block)
    time.sleep(0.01)
    cache.put("mittel", block)
    time.sleep(0.01)

    assert cache.get("alt") == block  # frischt den Zeitstempel auf
    time.sleep(0.01)

    cache.put("neu", block)
    assert cache.get("alt") == block, "die oft benutzte Datei darf nicht fliegen"
    assert cache.get("mittel") is None, "die am laengsten ungenutzte muss fliegen"


def test_treffer_frischt_den_zeitstempel_auf(tmp_path):
    cache = AudioCache(tmp_path, max_mb=1)
    cache.put("abc", b"daten")
    path = tmp_path / "abc.wav"
    os.utime(path, (1_000_000, 1_000_000))
    cache.get("abc")
    assert path.stat().st_mtime > 1_000_000


def test_legt_das_verzeichnis_selbst_an(tmp_path):
    target = tmp_path / "tief" / "audio"
    AudioCache(target, max_mb=1).put("abc", b"daten")
    assert (target / "abc.wav").exists()
