from collections.abc import Iterator
from functools import lru_cache
from sqlite3 import Connection

from app.config import settings
from app.content.loader import load_course
from app.content.models import Course
from app.db import get_connection
from app.ollama_client import OllamaClient


def get_db() -> Iterator[Connection]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_ollama() -> OllamaClient:
    return OllamaClient(host=settings.ollama_host, model=settings.ollama_model)


@lru_cache(maxsize=1)
def _load_course() -> Course:
    return load_course(settings.content_dir, language=settings.default_language)


def get_course() -> Course:
    """The content package, loaded once per process."""
    return _load_course()
