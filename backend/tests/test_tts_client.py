import json

import httpx
import pytest

from app.tts_client import TtsClient, TtsUnavailable


def _client(handler, **kwargs) -> TtsClient:
    client = TtsClient(host="http://tts:5001", **kwargs)
    client._transport = httpx.MockTransport(handler)
    return client


def test_synthesize_reicht_die_wav_bytes_durch():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["text"] = json.loads(request.read())["text"]
        return httpx.Response(200, content=b"RIFFfake")

    assert _client(handler).synthesize("дом") == b"RIFFfake"
    assert seen["path"] == "/synthesize"
    assert seen["text"] == "дом"


def test_verbindungsfehler_wird_zu_tts_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("kein Dienst", request=request)

    with pytest.raises(TtsUnavailable):
        _client(handler).synthesize("дом")


def test_zeitueberschreitung_wird_zu_tts_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("zu langsam", request=request)

    with pytest.raises(TtsUnavailable):
        _client(handler).synthesize("дом")


def test_fehlerstatus_wird_zu_tts_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"kaputt")

    with pytest.raises(TtsUnavailable):
        _client(handler).synthesize("дом")


def test_healthy_meldet_true_bei_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "ok", "voice": "ru_RU-dmitri-medium"})

    assert _client(handler).healthy() is True


def test_healthy_meldet_false_statt_zu_werfen():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("kein Dienst", request=request)

    assert _client(handler).healthy() is False


def test_healthy_meldet_false_bei_fehlerstatus():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    assert _client(handler).healthy() is False


def test_health_hat_eine_kuerzere_frist_als_die_synthese():
    # Beim Start wartet das Frontend darauf — dort sind 10 s zu lang.
    client = TtsClient(host="http://tts:5001")
    assert client._health_timeout < client._timeout
