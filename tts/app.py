"""Ein Dienst, eine Aufgabe: russischen Text zu WAV.

Bewusst ohne eigenen Zwischenspeicher — den fuehrt das Backend, weil dort schon
ein Volume liegt und die Auslieferung ohnehin ueber das Backend laeuft.

Der Piper-Import steht absichtlich *in* den Funktionen: so laesst sich das Modul
importieren und testen, ohne dass onnxruntime und ein 60-MB-Modell vorhanden
sein muessen.

Zwei Stimmen, weil zwei Figuren miteinander reden: die Rolle steht in der
Anfrage (`m`/`f`), welches Modell dahintersteht, entscheidet die Konfiguration.
"""

import io
import os
import wave

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

DEFAULT_ROLE = "m"
VOICES = {
    "m": os.environ.get("PIPER_VOICE", "ru_RU-denis-medium"),
    "f": os.environ.get("PIPER_VOICE_FEMALE", "ru_RU-irina-medium"),
}
# Die alte Variable bleibt: /health nennt sie weiter, und wer nur eine Stimme
# betreibt, hat nichts umzustellen.
VOICE = VOICES[DEFAULT_ROLE]
MODEL_DIR = os.environ.get("PIPER_MODEL_DIR", "/models")
LENGTH_SCALE = float(os.environ.get("PIPER_LENGTH_SCALE", "1.15"))
VOLUME = float(os.environ.get("PIPER_VOLUME", "1.0"))
MAX_CHARS = 300

app = FastAPI(title="Speaker TTS")

_loaded: dict[str, object] = {}


def _model_path(name: str) -> str:
    return os.path.join(MODEL_DIR, f"{name}.onnx")


def available_voices() -> dict[str, str]:
    """Welche Rollen wirklich ein Modell auf der Platte haben."""
    return {role: name for role, name in VOICES.items() if os.path.exists(_model_path(name))}


def voice_name(role: str | None) -> str:
    """Rolle auf den Modellnamen abbilden.

    Unbekannt oder nicht vorhanden heisst Vorgabestimme, nicht Fehler: eine
    fehlende zweite Stimme darf ein Gespraech hoechstens eintoenig machen, nie
    unhoerbar.
    """
    name = VOICES.get(role or DEFAULT_ROLE)
    if name is None or name not in available_voices().values():
        return VOICES[DEFAULT_ROLE]
    return name


def _load_voice(name: str):
    """Das ONNX-Modell einmal je Prozess laden — je Anfrage waere es zu teuer."""
    if name not in _loaded:
        from piper import PiperVoice

        _loaded[name] = PiperVoice.load(_model_path(name))
    return _loaded[name]


def synthesize_wav(text: str, voice_name_: str) -> bytes:
    from piper import SynthesisConfig

    voice = _load_voice(voice_name_)
    config = SynthesisConfig(volume=VOLUME, length_scale=LENGTH_SCALE)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=config)
    return buffer.getvalue()


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "voice": VOICE, "voices": available_voices()}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest) -> Response:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text ist leer")
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=400, detail=f"Text länger als {MAX_CHARS} Zeichen")
    return Response(
        content=synthesize_wav(text, voice_name(payload.voice)), media_type="audio/wav"
    )
