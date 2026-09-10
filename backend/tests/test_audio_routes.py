import pytest
from fastapi.testclient import TestClient

from app.audio.cache import AudioCache, audio_key
from app.config import settings
from app.dependencies import get_audio_cache, get_tts
from app.main import app
from app.tts_client import TtsUnavailable


class FakeTts:
    def __init__(self, *, healthy: bool = True, fail: bool = False):
        self._healthy = healthy
        self._fail = fail
        self.texts: list[str] = []
        self.voices: list[str] = []

    def synthesize(self, text: str, voice: str = "m") -> bytes:
        self.texts.append(text)
        self.voices.append(voice)
        if self._fail:
            raise TtsUnavailable("kein Dienst")
        return b"RIFF" + text.encode("utf-8")

    def healthy(self) -> bool:
        return self._healthy


@pytest.fixture
def cache(tmp_path) -> AudioCache:
    return AudioCache(tmp_path, max_mb=1)


@pytest.fixture
def client(cache):
    app.dependency_overrides[get_audio_cache] = lambda: cache
    yield TestClient(app)
    app.dependency_overrides.clear()


def _use(tts: FakeTts) -> None:
    app.dependency_overrides[get_tts] = lambda: tts


def test_liefert_wav_mit_dauerhaftem_cache_header(client):
    _use(FakeTts())
    response = client.get("/api/audio", params={"text": "дом"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert "immutable" in response.headers["cache-control"]
    assert response.content.startswith(b"RIFF")


def test_zweiter_abruf_fragt_den_dienst_nicht_erneut(client):
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "дом"})
    client.get("/api/audio", params={"text": "дом"})
    assert tts.texts == ["дом"]


def test_betonungszeichen_werden_vor_der_synthese_entfernt(client):
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "де́лаю"})
    assert tts.texts == ["делаю"]


def test_mit_und_ohne_betonung_treffen_denselben_eintrag(client):
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "де́лаю"})
    client.get("/api/audio", params={"text": "делаю"})
    assert tts.texts == ["делаю"], "die Betonung darf keinen zweiten Eintrag erzeugen"


def test_ablage_landet_unter_dem_erwarteten_schluessel(client, cache):
    _use(FakeTts())
    client.get("/api/audio", params={"text": "дом"})
    key = audio_key(
        "дом", voice=settings.piper_voice, length_scale=settings.piper_length_scale
    )
    assert cache.get(key) is not None


def test_zu_langer_text_wird_abgelehnt(client):
    _use(FakeTts())
    assert client.get("/api/audio", params={"text": "я" * 301}).status_code == 400


def test_leerer_text_wird_abgelehnt(client):
    _use(FakeTts())
    assert client.get("/api/audio", params={"text": "  "}).status_code == 400


def test_nicht_erreichbarer_dienst_ergibt_503(client):
    _use(FakeTts(fail=True))
    response = client.get("/api/audio", params={"text": "дом"})
    assert response.status_code == 503
    assert "nicht erreichbar" in response.json()["detail"]


def test_health_meldet_verfuegbar(client):
    _use(FakeTts(healthy=True))
    assert client.get("/api/audio/health").json() == {"available": True}


def test_health_meldet_nicht_verfuegbar(client):
    _use(FakeTts(healthy=False))
    assert client.get("/api/audio/health").json() == {"available": False}


def test_reicht_die_stimme_an_den_dienst_weiter(client):
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "дом", "voice": "f"})
    assert tts.voices == ["f"]


def test_ohne_angabe_spricht_die_maennliche_stimme(client):
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "дом"})
    assert tts.voices == ["m"]


def test_die_stimmen_teilen_sich_den_zwischenspeicher_nicht(client):
    # Sonst antwortete die zweite Figur mit der Stimme der ersten.
    tts = FakeTts()
    _use(tts)
    client.get("/api/audio", params={"text": "дом", "voice": "m"})
    client.get("/api/audio", params={"text": "дом", "voice": "f"})
    assert len(tts.texts) == 2


def test_der_schluessel_traegt_das_modell_der_stimme(client, cache):
    _use(FakeTts())
    client.get("/api/audio", params={"text": "дом", "voice": "f"})
    key = audio_key(
        "дом", voice=settings.piper_voice_female, length_scale=settings.piper_length_scale
    )
    assert cache.get(key) is not None


def test_unbekannte_stimme_wird_abgelehnt(client):
    _use(FakeTts())
    assert client.get("/api/audio", params={"text": "дом", "voice": "x"}).status_code == 422
