import io
import wave

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Der Dienst mit einer Piper-Attrappe.

    Ein 60-MB-Modell in der Testsuite zu laden waere absurd und wuerde die
    Laeufe an einen Download binden — geprueft wird die Huelle, nicht Piper.
    """
    import app as module

    def fake_synthesize(text: str) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(b"\x00\x00" * len(text))
        return buffer.getvalue()

    monkeypatch.setattr(module, "synthesize_wav", fake_synthesize)
    return TestClient(module.app)


def test_health_nennt_die_stimme(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["voice"] == "ru_RU-dmitri-medium"


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
