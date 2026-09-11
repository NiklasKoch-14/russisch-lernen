"""Ein Hörgespräch als eine Tonspur: zusammensetzen und über die Route ausliefern."""

import io
import wave

import pytest
from fastapi.testclient import TestClient

from app.audio.cache import AudioCache
from app.audio.track import join_wavs
from app.dependencies import get_audio_cache, get_course, get_tts
from app.main import app
from app.tts_client import TtsUnavailable
from tests.test_listening_service import _dialog, _lexeme

from app.content.models import Course

RATE = 22050


def _wav(seconds: float, *, rate: int = RATE) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(b"\x01\x00" * int(seconds * rate))
    return buffer.getvalue()


def _seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as track:
        return track.getnframes() / track.getframerate()


class TestJoinWavs:
    def test_setzt_die_zeilen_mit_pausen_hintereinander(self):
        track, starts = join_wavs([_wav(1.0), _wav(0.5), _wav(0.25)], pause_seconds=0.5)
        # Auf ganze Frames gerundet — eine Viertelsekunde sind 5512,5 davon.
        assert _seconds(track) == pytest.approx(1.0 + 0.5 + 0.5 + 0.5 + 0.25, abs=1e-3)
        assert starts == pytest.approx([0.0, 1.5, 2.5], abs=1e-3)

    def test_die_pause_ist_stille(self):
        track, _ = join_wavs([_wav(0.1), _wav(0.1)], pause_seconds=0.2)
        with wave.open(io.BytesIO(track)) as data:
            frames = data.readframes(data.getnframes())
        gap = frames[int(0.1 * RATE) * 2 : int(0.3 * RATE) * 2]
        assert set(gap) == {0}

    def test_verschiedene_formate_lassen_sich_nicht_mischen(self):
        # Eine neue Stimme mit anderer Abtastrate klaenge sonst zu schnell oder
        # zu langsam — lieber laut scheitern.
        with pytest.raises(ValueError, match="Format"):
            join_wavs([_wav(0.1), _wav(0.1, rate=16000)], pause_seconds=0.2)

    def test_ohne_zeilen_gibt_es_keine_spur(self):
        with pytest.raises(ValueError):
            join_wavs([], pause_seconds=0.2)


class WavTts:
    """Liefert je Text eine echte WAV, eine Zehntelsekunde je Zeichen."""

    def __init__(self, *, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple[str, str]] = []

    def synthesize(self, text: str, voice: str = "m") -> bytes:
        self.calls.append((text, voice))
        if self.fail:
            raise TtsUnavailable("kein Dienst")
        return _wav(0.1 * len(text))

    def healthy(self) -> bool:
        return not self.fail


@pytest.fixture
def course() -> Course:
    return Course(
        language="russian",
        lexemes={"da": _lexeme("da", "да", "da"), "net": _lexeme("net", "нет", "net")},
        units={},
        dialogs={1: _dialog(1, min_unit=5)},
    )


@pytest.fixture
def client(course, tmp_path):
    app.dependency_overrides[get_course] = lambda: course
    app.dependency_overrides[get_audio_cache] = lambda: AudioCache(tmp_path, max_mb=1)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_die_route_liefert_das_ganze_gespraech_als_eine_spur(client):
    tts = WavTts()
    app.dependency_overrides[get_tts] = lambda: tts
    response = client.get("/api/listening/1/audio")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    # да (m) · нет (f) · да (m) — jede Zeile in der Stimme ihrer Figur; das
    # zweite да kommt schon aus dem Zwischenspeicher.
    assert tts.calls == [("да", "m"), ("нет", "f")]
    starts = [float(value) for value in response.headers["x-line-starts"].split(",")]
    assert len(starts) == 3
    assert starts[0] == 0.0
    assert starts == sorted(starts)


def test_die_startzeiten_sind_fuer_den_browser_lesbar(client):
    # Ohne Expose-Header sieht fetch() im Browser den Header nicht.
    app.dependency_overrides[get_tts] = lambda: WavTts()
    response = client.get("/api/listening/1/audio", headers={"Origin": "http://localhost:3000"})
    assert "x-line-starts" in response.headers["access-control-expose-headers"].lower()


def test_ein_zweiter_abruf_erzeugt_nichts_neu(client):
    tts = WavTts()
    app.dependency_overrides[get_tts] = lambda: tts
    client.get("/api/listening/1/audio")
    client.get("/api/listening/1/audio")
    assert tts.calls == [("да", "m"), ("нет", "f")]


def test_ohne_sprachdienst_meldet_die_route_503(client):
    app.dependency_overrides[get_tts] = lambda: WavTts(fail=True)
    assert client.get("/api/listening/1/audio").status_code == 503


def test_ein_unbekanntes_gespraech_ist_404(client):
    app.dependency_overrides[get_tts] = lambda: WavTts()
    assert client.get("/api/listening/99/audio").status_code == 404
