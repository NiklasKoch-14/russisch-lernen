"""Ein Dienst, eine Aufgabe: russischen Text zu WAV.

Bewusst ohne eigenen Zwischenspeicher — den fuehrt das Backend, weil dort schon
ein Volume liegt und die Auslieferung ohnehin ueber das Backend laeuft.

Der Piper-Import steht absichtlich *in* den Funktionen: so laesst sich das Modul
importieren und testen, ohne dass onnxruntime und ein 60-MB-Modell vorhanden
sein muessen.
"""

import io
import os
import wave

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

VOICE = os.environ.get("PIPER_VOICE", "ru_RU-denis-medium")
MODEL_PATH = os.environ.get("PIPER_MODEL_PATH", f"/models/{VOICE}.onnx")
LENGTH_SCALE = float(os.environ.get("PIPER_LENGTH_SCALE", "1.15"))
VOLUME = float(os.environ.get("PIPER_VOLUME", "1.0"))
MAX_CHARS = 300

app = FastAPI(title="Speaker TTS")

_voice = None


def _load_voice():
    """Das ONNX-Modell einmal je Prozess laden — je Anfrage waere es zu teuer."""
    global _voice
    if _voice is None:
        from piper import PiperVoice

        _voice = PiperVoice.load(MODEL_PATH)
    return _voice


def synthesize_wav(text: str) -> bytes:
    from piper import SynthesisConfig

    voice = _load_voice()
    config = SynthesisConfig(volume=VOLUME, length_scale=LENGTH_SCALE)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=config)
    return buffer.getvalue()


class SynthesizeRequest(BaseModel):
    text: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "voice": VOICE}


@app.post("/synthesize")
def synthesize(payload: SynthesizeRequest) -> Response:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text ist leer")
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=400, detail=f"Text länger als {MAX_CHARS} Zeichen")
    return Response(content=synthesize_wav(text), media_type="audio/wav")
