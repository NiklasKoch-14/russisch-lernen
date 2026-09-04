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


settings = Settings()
