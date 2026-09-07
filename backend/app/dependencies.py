from collections.abc import Iterator
from functools import lru_cache
from sqlite3 import Connection

from app.audio.cache import AudioCache
from app.config import settings
from app.content.loader import load_course
from app.content.models import Course
from app.db import get_connection
from app.course.review_index import ReviewIndex, build_index
from app.ollama_client import OllamaClient
from app.tts_client import TtsClient


def get_db() -> Iterator[Connection]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_ollama() -> OllamaClient:
    return OllamaClient(host=settings.ollama_host, model=settings.ollama_model)


def get_tts() -> TtsClient:
    return TtsClient(host=settings.tts_host)


@lru_cache(maxsize=1)
def _audio_cache() -> AudioCache:
    return AudioCache(settings.audio_cache_dir, max_mb=settings.audio_cache_max_mb)


def get_audio_cache() -> AudioCache:
    return _audio_cache()


@lru_cache(maxsize=1)
def _load_course() -> Course:
    return load_course(settings.content_dir, language=settings.default_language)


def get_course() -> Course:
    """The content package, loaded once per process."""
    return _load_course()


@lru_cache(maxsize=1)
def _review_index() -> ReviewIndex:
    return build_index(_load_course())


def get_review_index() -> ReviewIndex:
    return _review_index()
