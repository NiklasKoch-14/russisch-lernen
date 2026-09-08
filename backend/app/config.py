import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONTENT_DIR = str(Path(__file__).resolve().parents[2] / "content" / "ru")


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    db_path: str = os.environ.get("DB_PATH", "./data/speaker.db")
    default_language: str = os.environ.get("DEFAULT_LANGUAGE", "russian")
    content_dir: str = os.environ.get("CONTENT_DIR", DEFAULT_CONTENT_DIR)
    game_dir: str = os.environ.get(
        "GAME_DIR", str(Path(__file__).resolve().parents[2] / "content" / "game")
    )
    tts_host: str = os.environ.get("TTS_HOST", "http://tts:5001")
    audio_cache_dir: str = os.environ.get("AUDIO_CACHE_DIR", "./data/audio")
    audio_cache_max_mb: int = int(os.environ.get("AUDIO_CACHE_MAX_MB", "50"))
    # Gehen in den Zwischenspeicher-Schluessel ein und muessen deshalb mit den
    # Werten des tts-Dienstes uebereinstimmen.
    piper_voice: str = os.environ.get("PIPER_VOICE", "ru_RU-denis-medium")
    piper_length_scale: float = float(os.environ.get("PIPER_LENGTH_SCALE", "1.15"))


settings = Settings()
