import io
import wave

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def gesprochen():
    """Mitschnitt der Attrappe: (Text, Modellname) je Aufruf."""
    return []


@pytest.fixture
def client(monkeypatch, gesprochen):
    """Der Dienst mit einer Piper-Attrappe.

    Ein 60-MB-Modell in der Testsuite zu laden waere absurd und wuerde die
    Laeufe an einen Download binden — geprueft wird die Huelle, nicht Piper.
    """
    import app as module

    def fake_synthesize(text: str, voice_name: str) -> bytes:
        gesprochen.append((text, voice_name))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x00\x00" * len(text))
        return buffer.getvalue()

    monkeypatch.setattr(module, "synthesize_wav", fake_synthesize)
    monkeypatch.setattr(module, "available_voices", lambda: dict(module.VOICES))
    return TestClient(module.app)


def test_health_nennt_die_stimme(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["voice"] == "ru_RU-denis-medium"


def test_health_nennt_beide_stimmen(client):
    body = client.get("/health").json()
    assert body["voices"] == {"m": "ru_RU-denis-medium", "f": "ru_RU-irina-medium"}


def test_synthesize_nimmt_die_weibliche_stimme(client, gesprochen):
    response = client.post("/synthesize", json={"text": "дом", "voice": "f"})
    assert response.status_code == 200
    assert gesprochen[-1] == ("дом", "ru_RU-irina-medium")


def test_ohne_angabe_spricht_die_vorgabestimme(client, gesprochen):
    client.post("/synthesize", json={"text": "дом"})
    assert gesprochen[-1] == ("дом", "ru_RU-denis-medium")


def test_unbekannte_stimme_faellt_auf_die_vorgabe_zurueck(client, gesprochen):
    # Eine fehlende Stimme darf ein Gespraech hoechstens eintoenig machen,
    # nie unhoerbar — deshalb kein Fehler.
    response = client.post("/synthesize", json={"text": "дом", "voice": "x"})
    assert response.status_code == 200
    assert gesprochen[-1] == ("дом", "ru_RU-denis-medium")


def test_synthesize_liefert_wav(client):
    response = client.post("/synthesize", json={"text": "дом"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content.startswith(b"RIFF")


def test_leerer_text_wird_abgelehnt(client):
    assert client.post("/synthesize", json={"text": "   "}).status_code == 400


def test_zu_langer_text_wird_abgelehnt(client):
    assert client.post("/synthesize", json={"text": "я" * 301}).status_code == 400


def test_text_wird_vor_der_synthese_getrimmt(client):
    response = client.post("/synthesize", json={"text": "  дом  "})
    assert response.status_code == 200
    # Die Attrappe schreibt zwei Byte je Zeichen — 3 Zeichen, nicht 7.
    with wave.open(io.BytesIO(response.content), "rb") as wav:
        assert wav.getnframes() == 3
