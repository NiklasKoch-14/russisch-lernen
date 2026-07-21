from collections.abc import Iterator
from sqlite3 import Connection

from app.config import settings
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
