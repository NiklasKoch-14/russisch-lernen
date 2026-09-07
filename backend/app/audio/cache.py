import hashlib
import re
import time
from pathlib import Path

# Kombinierendes Akut. Steht im Content zur Betonung; espeak-ng kennt es fuer
# Russisch nicht und macht daraus Artefakte — gemessen wird derselbe Satz mit
# Zeichen laenger als ohne. Also raus, bevor synthetisiert wird.
_COMBINING_ACUTE = re.compile("́")


def strip_stress(text: str) -> str:
    return _COMBINING_ACUTE.sub("", text)


def audio_key(text: str, *, voice: str, length_scale: float) -> str:
    """Inhaltsbestimmter Schluessel — deshalb darf die Antwort `immutable` heissen."""
    raw = f"{voice}|{length_scale}|{text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class AudioCache:
    """Dateien auf der Platte mit hartem Deckel.

    Verdraengt wird nach Zeitstempel, und jeder Treffer frischt ihn auf. Ohne das
    waere es „aeltestes zuerst" statt „am laengsten nicht gebraucht" — und die
    Saetze aus Einheit 1 flogen als Erstes, obwohl sie in der Wiederholung am
    haeufigsten drankommen.
    """

    def __init__(self, directory: str | Path, max_mb: int):
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max_bytes = max_mb * 1024 * 1024

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.wav"

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        path.touch()
        return path.read_bytes()

    def put(self, key: str, data: bytes) -> None:
        self._path(key).write_bytes(data)
        self._evict()

    def total_bytes(self) -> int:
        return sum(path.stat().st_size for path in self._dir.glob("*.wav"))

    def _evict(self) -> None:
        files = sorted(self._dir.glob("*.wav"), key=lambda path: path.stat().st_mtime)
        total = sum(path.stat().st_size for path in files)
        for path in files:
            if total <= self._max_bytes:
                return
            total -= path.stat().st_size
            path.unlink(missing_ok=True)
