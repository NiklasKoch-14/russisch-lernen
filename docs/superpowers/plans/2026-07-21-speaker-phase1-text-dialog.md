# Speaker Phase 1 (Text Dialog) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the text-based Phase 1 of the Speaker language-tutor app: an AI tutor dialog (via local Ollama, no API keys), CEFR proficiency tracking with placement + ongoing reassessment, a periodically regenerated learning plan, and a vocabulary flashcard system with SM-2 spaced repetition — all served by a React frontend and FastAPI backend, deployed via a single `docker compose up`.

**Architecture:** A Python/FastAPI backend (SQLite persistence, no ORM — thin repository modules over raw `sqlite3`) orchestrates calls to a local Ollama container for all AI behavior (tutoring, placement, session analysis, learning-plan generation). A React (Vite + TypeScript) single-page frontend talks to the backend over a JSON HTTP API. All three services (`frontend`, `backend`, `ollama`) run in Docker Compose; an `ollama-init` one-shot service pulls the configured model on first start. Voice (STT/TTS) is explicitly out of scope — this phase is text-only.

**Tech Stack:** Python 3.11, FastAPI, uvicorn, httpx, pydantic v2, stdlib `sqlite3`, pytest. React 18, TypeScript, Vite, Vitest, Testing Library. Docker Compose. Ollama (`llama3.2:3b` default model).

## Global Constraints

- No API key may ever be required or configured anywhere in the stack — all AI inference is local via the `ollama` container.
- Target runtime is CPU-only (no GPU) — keep model choices and code paths CPU-friendly; default Ollama model is `llama3.2:3b`, overridable via the `OLLAMA_MODEL` env var.
- Single-user app: no authentication/login, no multi-tenancy. `profile` table always has exactly one row (`id = 1`).
- UI copy is in German; learning content (tutor dialog, vocab, placement) is in the learner's target language (English content only in Phase 1, but code must not hardcode "english" — always read the language from the profile/settings).
- Persistence is SQLite; no external database service.
- Everything must come up via a single `docker compose up`; no manual post-start configuration steps other than waiting for the first-run Ollama model pull.
- Voice (microphone input, STT, TTS) is out of scope for this plan — do not add audio endpoints or UI in this phase.

---

## Backend

### Task 1: Backend scaffolding — FastAPI health check, Dockerfile, docker-compose skeleton

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/main.py`
- Create: `backend/Dockerfile`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_main.py`
- Create: `docker-compose.yml`

**Interfaces:**
- Produces: `app.config.settings` — a `Settings` dataclass instance with fields `ollama_host: str`, `ollama_model: str`, `db_path: str`, `default_language: str`, each read from an env var with a sane default.
- Produces: `app.main.app` — the FastAPI application instance, with `GET /api/health` returning `{"status": "ok"}`.

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.9.2
pytest==8.3.3
```

- [ ] **Step 2: Create a virtualenv and install dependencies**

Run:
```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
```
Expected: dependencies install without errors.

- [ ] **Step 3: Write the failing test**

Create `backend/tests/__init__.py` (empty file).

Create `backend/tests/test_main.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 5: Implement `app/config.py`**

```python
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    ollama_host: str = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
    db_path: str = os.environ.get("DB_PATH", "./data/speaker.db")
    default_language: str = os.environ.get("DEFAULT_LANGUAGE", "english")


settings = Settings()
```

Create `backend/app/__init__.py` (empty file).

- [ ] **Step 6: Implement `app/main.py`**

```python
from fastapi import FastAPI

app = FastAPI(title="Speaker Backend")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_main.py -v`
Expected: PASS (1 passed)

- [ ] **Step 8: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 9: Create root `docker-compose.yml`**

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

  backend:
    build: ./backend
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2:3b}
      - DB_PATH=/data/speaker.db
      - DEFAULT_LANGUAGE=english
    volumes:
      - backend_data:/data
    ports:
      - "8000:8000"
    depends_on:
      - ollama

volumes:
  ollama_data:
  backend_data:
```

- [ ] **Step 10: Verify the backend container builds and serves health**

Run:
```bash
docker compose up -d --build backend ollama
sleep 3
curl -sf http://localhost:8000/api/health
docker compose down
```
Expected: prints `{"status":"ok"}`, no errors.

- [ ] **Step 11: Commit**

```bash
git add backend/requirements.txt backend/app backend/Dockerfile backend/tests docker-compose.yml
git commit -m "feat: add backend scaffolding with health endpoint and docker-compose skeleton"
```

---

### Task 2: Database layer — schema and connection helpers

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `get_connection(db_path: str) -> sqlite3.Connection` (row factory `sqlite3.Row`, foreign keys on). `init_db(db_path: str) -> None` creates all tables if missing. `db_session(db_path: str)` — a context manager yielding a connection and committing on exit. Pytest fixtures `db_path` and `conn` in `conftest.py`, usable by all later backend tests.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_db.py
from app.db import init_db, db_session


def test_init_db_creates_all_tables(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    with db_session(db_path) as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    expected = {
        "profile", "learning_plans", "conversation_sessions",
        "conversation_turns", "session_analyses", "vocab_cards", "quiz_attempts",
    }
    assert expected.issubset(tables)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 3: Implement `app/db.py`**

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    language TEXT NOT NULL,
    cefr_level TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    topics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    session_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES conversation_sessions(id),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS session_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES conversation_sessions(id),
    updated_level TEXT,
    notable_errors_json TEXT NOT NULL,
    vocab_suggestions_json TEXT NOT NULL,
    next_topics_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vocab_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    term TEXT NOT NULL,
    translation TEXT NOT NULL,
    example_sentence TEXT NOT NULL,
    source_session_id INTEGER REFERENCES conversation_sessions(id),
    interval_days REAL NOT NULL DEFAULT 0,
    ease_factor REAL NOT NULL DEFAULT 2.5,
    repetitions INTEGER NOT NULL DEFAULT 0,
    due_date TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES vocab_cards(id),
    user_answer TEXT NOT NULL,
    correct INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def db_session(db_path: str):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_db.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Create shared pytest fixtures for later tasks**

```python
# backend/tests/conftest.py
import pytest

from app.db import get_connection, init_db


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = get_connection(db_path)
    yield connection
    connection.close()
```

- [ ] **Step 6: Run the full test suite to confirm nothing broke**

Run: `cd backend && . .venv/bin/activate && python -m pytest -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/app/db.py backend/tests/conftest.py backend/tests/test_db.py
git commit -m "feat: add SQLite schema, connection helpers, and shared test fixtures"
```

---

### Task 3: Profile repository

**Files:**
- Create: `backend/app/repositories/__init__.py`
- Create: `backend/app/repositories/profile_repo.py`
- Test: `backend/tests/test_profile_repo.py`

**Interfaces:**
- Consumes: `conn` fixture (Task 2).
- Produces: `Profile` dataclass (`language: str`, `cefr_level: str`, `created_at: str`). `get_or_create_profile(conn, default_language: str) -> Profile`. `update_profile(conn, *, language: str | None = None, cefr_level: str | None = None) -> Profile`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_profile_repo.py
from app.repositories.profile_repo import get_or_create_profile, update_profile


def test_get_or_create_profile_creates_default_on_first_call(conn):
    profile = get_or_create_profile(conn, default_language="english")
    assert profile.language == "english"
    assert profile.cefr_level == "UNPLACED"


def test_get_or_create_profile_returns_existing_on_second_call(conn):
    get_or_create_profile(conn, default_language="english")
    profile = get_or_create_profile(conn, default_language="spanish")
    assert profile.language == "english"


def test_update_profile_changes_level(conn):
    get_or_create_profile(conn, default_language="english")
    updated = update_profile(conn, cefr_level="B1")
    assert updated.cefr_level == "B1"
    assert updated.language == "english"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_profile_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories'`

- [ ] **Step 3: Implement the repository**

Create `backend/app/repositories/__init__.py` (empty file).

```python
# backend/app/repositories/profile_repo.py
import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class Profile:
    language: str
    cefr_level: str
    created_at: str


def get_or_create_profile(conn: Connection, default_language: str) -> Profile:
    row = conn.execute(
        "SELECT language, cefr_level, created_at FROM profile WHERE id = 1"
    ).fetchone()
    if row is not None:
        return Profile(language=row["language"], cefr_level=row["cefr_level"], created_at=row["created_at"])

    created_at = dt.datetime.utcnow().isoformat()
    conn.execute(
        "INSERT INTO profile (id, language, cefr_level, created_at) VALUES (1, ?, ?, ?)",
        (default_language, "UNPLACED", created_at),
    )
    conn.commit()
    return Profile(language=default_language, cefr_level="UNPLACED", created_at=created_at)


def update_profile(
    conn: Connection, *, language: str | None = None, cefr_level: str | None = None
) -> Profile:
    current = get_or_create_profile(conn, default_language=language or "english")
    new_language = language if language is not None else current.language
    new_level = cefr_level if cefr_level is not None else current.cefr_level
    conn.execute(
        "UPDATE profile SET language = ?, cefr_level = ? WHERE id = 1",
        (new_language, new_level),
    )
    conn.commit()
    return Profile(language=new_language, cefr_level=new_level, created_at=current.created_at)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_profile_repo.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/__init__.py backend/app/repositories/profile_repo.py backend/tests/test_profile_repo.py
git commit -m "feat: add profile repository"
```

---

### Task 4: SM-2 spaced-repetition algorithm

**Files:**
- Create: `backend/app/srs/__init__.py`
- Create: `backend/app/srs/sm2.py`
- Test: `backend/tests/test_sm2.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SM2Result` dataclass (`repetitions: int`, `ease_factor: float`, `interval_days: float`). `sm2_update(*, correct: bool, repetitions: int, ease_factor: float, interval_days: float) -> SM2Result`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_sm2.py
from app.srs.sm2 import sm2_update


def test_first_correct_answer_sets_interval_to_one_day():
    result = sm2_update(correct=True, repetitions=0, ease_factor=2.5, interval_days=0)
    assert result.repetitions == 1
    assert result.interval_days == 1.0
    assert result.ease_factor == 2.5


def test_second_correct_answer_sets_interval_to_six_days():
    result = sm2_update(correct=True, repetitions=1, ease_factor=2.5, interval_days=1.0)
    assert result.repetitions == 2
    assert result.interval_days == 6.0


def test_third_correct_answer_multiplies_interval_by_ease_factor():
    result = sm2_update(correct=True, repetitions=2, ease_factor=2.5, interval_days=6.0)
    assert result.repetitions == 3
    assert result.interval_days == 15.0


def test_incorrect_answer_resets_repetitions_and_interval():
    result = sm2_update(correct=False, repetitions=3, ease_factor=2.5, interval_days=15.0)
    assert result.repetitions == 0
    assert result.interval_days == 1.0
    assert result.ease_factor == 2.18


def test_ease_factor_never_drops_below_1_3():
    result = sm2_update(correct=False, repetitions=0, ease_factor=1.35, interval_days=1.0)
    assert result.ease_factor >= 1.3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_sm2.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.srs'`

- [ ] **Step 3: Implement the algorithm**

Create `backend/app/srs/__init__.py` (empty file).

```python
# backend/app/srs/sm2.py
from dataclasses import dataclass


@dataclass
class SM2Result:
    repetitions: int
    ease_factor: float
    interval_days: float


def sm2_update(*, correct: bool, repetitions: int, ease_factor: float, interval_days: float) -> SM2Result:
    quality = 4 if correct else 2

    if quality >= 3:
        if repetitions == 0:
            new_interval = 1.0
        elif repetitions == 1:
            new_interval = 6.0
        else:
            new_interval = round(interval_days * ease_factor, 2)
        new_repetitions = repetitions + 1
    else:
        new_repetitions = 0
        new_interval = 1.0

    new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    new_ease_factor = max(1.3, round(new_ease_factor, 3))

    return SM2Result(repetitions=new_repetitions, ease_factor=new_ease_factor, interval_days=new_interval)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_sm2.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/srs/__init__.py backend/app/srs/sm2.py backend/tests/test_sm2.py
git commit -m "feat: add SM-2 spaced-repetition algorithm"
```

---

### Task 5: Vocabulary repository and grading service

**Files:**
- Create: `backend/app/repositories/vocab_repo.py`
- Create: `backend/app/srs/vocab_service.py`
- Test: `backend/tests/test_vocab_repo.py`
- Test: `backend/tests/test_vocab_service.py`

**Interfaces:**
- Consumes: `conn` fixture (Task 2), `sm2_update`/`SM2Result` (Task 4).
- Produces: `VocabCard` dataclass (`id: int`, `language: str`, `term: str`, `translation: str`, `example_sentence: str`, `interval_days: float`, `ease_factor: float`, `repetitions: int`, `due_date: str`). `create_card(conn, *, language, term, translation, example_sentence, source_session_id=None) -> VocabCard`. `get_due_cards(conn, *, language, as_of=None) -> list[VocabCard]`. `get_card_by_id(conn, *, card_id) -> VocabCard | None`. `update_srs_state(conn, *, card_id, repetitions, ease_factor, interval_days, due_date) -> None`. `record_quiz_attempt(conn, *, card_id, user_answer, correct) -> None`. `is_answer_correct(user_answer, expected_translation) -> bool`. `submit_answer(conn, *, card: VocabCard, user_answer: str) -> bool`.

- [ ] **Step 1: Write the failing repository tests**

```python
# backend/tests/test_vocab_repo.py
import datetime as dt

from app.repositories import vocab_repo


def test_create_card_defaults_to_due_today(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="This is my house."
    )
    assert card.due_date == dt.date.today().isoformat()
    assert card.repetitions == 0
    assert card.ease_factor == 2.5


def test_get_due_cards_only_returns_cards_due_on_or_before_as_of(conn):
    vocab_repo.create_card(conn, language="english", term="house", translation="Haus", example_sentence="x")
    future_card = vocab_repo.create_card(
        conn, language="english", term="cat", translation="Katze", example_sentence="x"
    )
    vocab_repo.update_srs_state(
        conn, card_id=future_card.id, repetitions=1, ease_factor=2.5, interval_days=30, due_date="2099-01-01"
    )

    due = vocab_repo.get_due_cards(conn, language="english")

    assert [c.term for c in due] == ["house"]


def test_get_card_by_id_returns_none_when_missing(conn):
    assert vocab_repo.get_card_by_id(conn, card_id=999) is None


def test_record_quiz_attempt_inserts_row(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="x"
    )
    vocab_repo.record_quiz_attempt(conn, card_id=card.id, user_answer="Haus", correct=True)
    row = conn.execute("SELECT * FROM quiz_attempts WHERE card_id = ?", (card.id,)).fetchone()
    assert row["correct"] == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_vocab_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.vocab_repo'`

- [ ] **Step 3: Implement `app/repositories/vocab_repo.py`**

```python
import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class VocabCard:
    id: int
    language: str
    term: str
    translation: str
    example_sentence: str
    interval_days: float
    ease_factor: float
    repetitions: int
    due_date: str


_COLUMNS = (
    "id, language, term, translation, example_sentence, "
    "interval_days, ease_factor, repetitions, due_date"
)


def create_card(
    conn: Connection,
    *,
    language: str,
    term: str,
    translation: str,
    example_sentence: str,
    source_session_id: int | None = None,
) -> VocabCard:
    now = dt.datetime.utcnow()
    due_date = now.date().isoformat()
    created_at = now.isoformat()
    cursor = conn.execute(
        """INSERT INTO vocab_cards
           (language, term, translation, example_sentence, source_session_id,
            interval_days, ease_factor, repetitions, due_date, created_at)
           VALUES (?, ?, ?, ?, ?, 0, 2.5, 0, ?, ?)""",
        (language, term, translation, example_sentence, source_session_id, due_date, created_at),
    )
    conn.commit()
    return VocabCard(
        id=cursor.lastrowid,
        language=language,
        term=term,
        translation=translation,
        example_sentence=example_sentence,
        interval_days=0,
        ease_factor=2.5,
        repetitions=0,
        due_date=due_date,
    )


def get_due_cards(conn: Connection, *, language: str, as_of: str | None = None) -> list[VocabCard]:
    as_of = as_of or dt.date.today().isoformat()
    rows = conn.execute(
        f"""SELECT {_COLUMNS} FROM vocab_cards
           WHERE language = ? AND due_date <= ?
           ORDER BY due_date ASC""",
        (language, as_of),
    ).fetchall()
    return [VocabCard(**dict(row)) for row in rows]


def get_card_by_id(conn: Connection, *, card_id: int) -> VocabCard | None:
    row = conn.execute(f"SELECT {_COLUMNS} FROM vocab_cards WHERE id = ?", (card_id,)).fetchone()
    if row is None:
        return None
    return VocabCard(**dict(row))


def update_srs_state(
    conn: Connection,
    *,
    card_id: int,
    repetitions: int,
    ease_factor: float,
    interval_days: float,
    due_date: str,
) -> None:
    conn.execute(
        """UPDATE vocab_cards
           SET repetitions = ?, ease_factor = ?, interval_days = ?, due_date = ?
           WHERE id = ?""",
        (repetitions, ease_factor, interval_days, due_date, card_id),
    )
    conn.commit()


def record_quiz_attempt(conn: Connection, *, card_id: int, user_answer: str, correct: bool) -> None:
    conn.execute(
        "INSERT INTO quiz_attempts (card_id, user_answer, correct, created_at) VALUES (?, ?, ?, ?)",
        (card_id, user_answer, int(correct), dt.datetime.utcnow().isoformat()),
    )
    conn.commit()
```

- [ ] **Step 4: Run repository tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_vocab_repo.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Write the failing service tests**

```python
# backend/tests/test_vocab_service.py
from app.repositories import vocab_repo
from app.srs.vocab_service import is_answer_correct, submit_answer


def test_is_answer_correct_exact_match():
    assert is_answer_correct("Haus", "Haus") is True


def test_is_answer_correct_case_and_whitespace_insensitive():
    assert is_answer_correct("  haus  ", "Haus") is True


def test_is_answer_correct_tolerates_small_typo():
    assert is_answer_correct("beautifull", "beautiful") is True


def test_is_answer_correct_rejects_wrong_word():
    assert is_answer_correct("Katze", "Haus") is False


def test_submit_answer_updates_srs_state_and_records_attempt(conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="x"
    )

    correct = submit_answer(conn, card=card, user_answer="Haus")

    assert correct is True
    updated = vocab_repo.get_card_by_id(conn, card_id=card.id)
    assert updated.repetitions == 1
    assert updated.interval_days == 1.0
    row = conn.execute("SELECT * FROM quiz_attempts WHERE card_id = ?", (card.id,)).fetchone()
    assert row["correct"] == 1
```

- [ ] **Step 6: Run service tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_vocab_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.srs.vocab_service'`

- [ ] **Step 7: Implement `app/srs/vocab_service.py`**

```python
import datetime as dt
from difflib import SequenceMatcher
from sqlite3 import Connection

from app.repositories import vocab_repo
from app.srs.sm2 import sm2_update

CORRECT_THRESHOLD = 0.85


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def is_answer_correct(user_answer: str, expected_translation: str) -> bool:
    ratio = SequenceMatcher(None, _normalize(user_answer), _normalize(expected_translation)).ratio()
    return ratio >= CORRECT_THRESHOLD


def submit_answer(conn: Connection, *, card: vocab_repo.VocabCard, user_answer: str) -> bool:
    correct = is_answer_correct(user_answer, card.translation)
    result = sm2_update(
        correct=correct,
        repetitions=card.repetitions,
        ease_factor=card.ease_factor,
        interval_days=card.interval_days,
    )
    due_date = (dt.date.today() + dt.timedelta(days=result.interval_days)).isoformat()
    vocab_repo.update_srs_state(
        conn,
        card_id=card.id,
        repetitions=result.repetitions,
        ease_factor=result.ease_factor,
        interval_days=result.interval_days,
        due_date=due_date,
    )
    vocab_repo.record_quiz_attempt(conn, card_id=card.id, user_answer=user_answer, correct=correct)
    return correct
```

- [ ] **Step 8: Run service tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_vocab_service.py -v`
Expected: PASS (5 passed)

- [ ] **Step 9: Commit**

```bash
git add backend/app/repositories/vocab_repo.py backend/app/srs/vocab_service.py backend/tests/test_vocab_repo.py backend/tests/test_vocab_service.py
git commit -m "feat: add vocabulary repository and SM-2-backed grading service"
```

---

### Task 6: Ollama client wrapper

**Files:**
- Create: `backend/app/ollama_client.py`
- Test: `backend/tests/test_ollama_client.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `OllamaClient(host: str, model: str, timeout: float = 60.0)` with method `chat(messages: list[dict[str, str]]) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_ollama_client.py
from unittest.mock import MagicMock, patch

from app.ollama_client import OllamaClient


def test_chat_posts_to_ollama_and_returns_message_content():
    client = OllamaClient(host="http://ollama:11434", model="llama3.2:3b")
    fake_response = MagicMock()
    fake_response.json.return_value = {"message": {"role": "assistant", "content": "Hello!"}}
    fake_response.raise_for_status.return_value = None

    with patch("app.ollama_client.httpx.post", return_value=fake_response) as mock_post:
        result = client.chat([{"role": "user", "content": "Hi"}])

    assert result == "Hello!"
    mock_post.assert_called_once()
    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["json"]["model"] == "llama3.2:3b"
    assert called_kwargs["json"]["messages"] == [{"role": "user", "content": "Hi"}]
    assert called_kwargs["json"]["stream"] is False


def test_chat_raises_on_http_error():
    import httpx

    client = OllamaClient(host="http://ollama:11434", model="llama3.2:3b")
    fake_response = MagicMock()
    fake_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "error", request=MagicMock(), response=MagicMock()
    )

    with patch("app.ollama_client.httpx.post", return_value=fake_response):
        try:
            client.chat([{"role": "user", "content": "Hi"}])
            assert False, "expected HTTPStatusError"
        except httpx.HTTPStatusError:
            pass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_ollama_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.ollama_client'`

- [ ] **Step 3: Implement `app/ollama_client.py`**

```python
import httpx


class OllamaClient:
    def __init__(self, host: str, model: str, timeout: float = 60.0):
        self._host = host.rstrip("/")
        self._model = model
        self._timeout = timeout

    def chat(self, messages: list[dict[str, str]]) -> str:
        response = httpx.post(
            f"{self._host}/api/chat",
            json={"model": self._model, "messages": messages, "stream": False},
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_ollama_client.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ollama_client.py backend/tests/test_ollama_client.py
git commit -m "feat: add Ollama HTTP client wrapper"
```

---

### Task 7: Conversation session and turn repository

**Files:**
- Create: `backend/app/repositories/session_repo.py`
- Test: `backend/tests/test_session_repo.py`

**Interfaces:**
- Consumes: `conn` fixture (Task 2).
- Produces: `ConversationTurn` dataclass (`role: str`, `content: str`). `create_session(conn, *, language, session_type) -> int`. `end_session(conn, *, session_id) -> None`. `add_turn(conn, *, session_id, role, content) -> None`. `get_turns(conn, *, session_id) -> list[ConversationTurn]`. `get_active_session(conn, *, language, session_type) -> int | None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_session_repo.py
from app.repositories import session_repo


def test_create_session_returns_an_id(conn):
    session_id = session_repo.create_session(conn, language="english", session_type="practice")
    assert isinstance(session_id, int)


def test_add_turn_and_get_turns_round_trip(conn):
    session_id = session_repo.create_session(conn, language="english", session_type="practice")
    session_repo.add_turn(conn, session_id=session_id, role="user", content="Hi")
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content="Hello!")

    turns = session_repo.get_turns(conn, session_id=session_id)

    assert [(t.role, t.content) for t in turns] == [("user", "Hi"), ("assistant", "Hello!")]


def test_get_active_session_ignores_ended_sessions(conn):
    session_id = session_repo.create_session(conn, language="english", session_type="practice")
    session_repo.end_session(conn, session_id=session_id)

    assert session_repo.get_active_session(conn, language="english", session_type="practice") is None


def test_get_active_session_returns_most_recent_open_session(conn):
    session_repo.create_session(conn, language="english", session_type="practice")
    second_id = session_repo.create_session(conn, language="english", session_type="practice")

    assert session_repo.get_active_session(conn, language="english", session_type="practice") == second_id
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_session_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.session_repo'`

- [ ] **Step 3: Implement `app/repositories/session_repo.py`**

```python
import datetime as dt
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class ConversationTurn:
    role: str
    content: str


def create_session(conn: Connection, *, language: str, session_type: str) -> int:
    started_at = dt.datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO conversation_sessions (language, session_type, started_at) VALUES (?, ?, ?)",
        (language, session_type, started_at),
    )
    conn.commit()
    return cursor.lastrowid


def end_session(conn: Connection, *, session_id: int) -> None:
    conn.execute(
        "UPDATE conversation_sessions SET ended_at = ? WHERE id = ?",
        (dt.datetime.utcnow().isoformat(), session_id),
    )
    conn.commit()


def add_turn(conn: Connection, *, session_id: int, role: str, content: str) -> None:
    conn.execute(
        "INSERT INTO conversation_turns (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, dt.datetime.utcnow().isoformat()),
    )
    conn.commit()


def get_turns(conn: Connection, *, session_id: int) -> list[ConversationTurn]:
    rows = conn.execute(
        "SELECT role, content FROM conversation_turns WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    return [ConversationTurn(role=row["role"], content=row["content"]) for row in rows]


def get_active_session(conn: Connection, *, language: str, session_type: str) -> int | None:
    row = conn.execute(
        """SELECT id FROM conversation_sessions
           WHERE language = ? AND session_type = ? AND ended_at IS NULL
           ORDER BY id DESC LIMIT 1""",
        (language, session_type),
    ).fetchone()
    return row["id"] if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_session_repo.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/session_repo.py backend/tests/test_session_repo.py
git commit -m "feat: add conversation session and turn repository"
```

---

### Task 8: Learning plan repository

**Files:**
- Create: `backend/app/repositories/learning_plan_repo.py`
- Test: `backend/tests/test_learning_plan_repo.py`

**Interfaces:**
- Consumes: `conn` fixture (Task 2).
- Produces: `LearningPlan` dataclass (`id: int`, `language: str`, `topics: list[str]`, `created_at: str`). `create_plan(conn, *, language, topics: list[str]) -> LearningPlan`. `get_latest_plan(conn, *, language) -> LearningPlan | None`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_learning_plan_repo.py
from app.repositories.learning_plan_repo import create_plan, get_latest_plan


def test_get_latest_plan_returns_none_when_no_plan_exists(conn):
    assert get_latest_plan(conn, language="english") is None


def test_create_plan_and_get_latest_plan_round_trip(conn):
    create_plan(conn, language="english", topics=["Ordering food", "Small talk"])

    plan = get_latest_plan(conn, language="english")

    assert plan.topics == ["Ordering food", "Small talk"]


def test_get_latest_plan_returns_most_recently_created(conn):
    create_plan(conn, language="english", topics=["Old topic"])
    create_plan(conn, language="english", topics=["New topic"])

    plan = get_latest_plan(conn, language="english")

    assert plan.topics == ["New topic"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_learning_plan_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.repositories.learning_plan_repo'`

- [ ] **Step 3: Implement `app/repositories/learning_plan_repo.py`**

```python
import datetime as dt
import json
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class LearningPlan:
    id: int
    language: str
    topics: list[str]
    created_at: str


def create_plan(conn: Connection, *, language: str, topics: list[str]) -> LearningPlan:
    created_at = dt.datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO learning_plans (language, topics_json, created_at) VALUES (?, ?, ?)",
        (language, json.dumps(topics), created_at),
    )
    conn.commit()
    return LearningPlan(id=cursor.lastrowid, language=language, topics=topics, created_at=created_at)


def get_latest_plan(conn: Connection, *, language: str) -> LearningPlan | None:
    row = conn.execute(
        """SELECT id, language, topics_json, created_at FROM learning_plans
           WHERE language = ? ORDER BY id DESC LIMIT 1""",
        (language,),
    ).fetchone()
    if row is None:
        return None
    return LearningPlan(
        id=row["id"],
        language=row["language"],
        topics=json.loads(row["topics_json"]),
        created_at=row["created_at"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_learning_plan_repo.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/repositories/learning_plan_repo.py backend/tests/test_learning_plan_repo.py
git commit -m "feat: add learning plan repository"
```

---

### Task 9: Tutor prompt templates

**Files:**
- Create: `backend/app/tutor/__init__.py`
- Create: `backend/app/tutor/prompts.py`
- Test: `backend/tests/test_prompts.py`

**Interfaces:**
- Consumes: `ConversationTurn` (Task 7).
- Produces: `tutor_system_prompt(*, language, cefr_level, plan_topic: str | None) -> str`. `placement_system_prompt(*, language) -> str`. `build_chat_messages(*, system_prompt: str, history: list[ConversationTurn], user_message: str) -> list[dict]`. `analysis_prompt(*, language, cefr_level, transcript: str) -> str`. `learning_plan_prompt(*, language, cefr_level, notes: str) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_prompts.py
from app.repositories.session_repo import ConversationTurn
from app.tutor.prompts import (
    analysis_prompt,
    build_chat_messages,
    learning_plan_prompt,
    placement_system_prompt,
    tutor_system_prompt,
)


def test_tutor_system_prompt_includes_language_and_level():
    prompt = tutor_system_prompt(language="english", cefr_level="B1", plan_topic=None)
    assert "english" in prompt
    assert "B1" in prompt


def test_tutor_system_prompt_includes_plan_topic_when_present():
    prompt = tutor_system_prompt(language="english", cefr_level="B1", plan_topic="Ordering food")
    assert "Ordering food" in prompt


def test_placement_system_prompt_includes_language_and_json_instruction():
    prompt = placement_system_prompt(language="english")
    assert "english" in prompt
    assert '"level"' in prompt


def test_build_chat_messages_orders_system_history_then_user():
    history = [ConversationTurn(role="user", content="Hi"), ConversationTurn(role="assistant", content="Hello")]
    messages = build_chat_messages(system_prompt="SYS", history=history, user_message="Bye")

    assert messages == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Bye"},
    ]


def test_analysis_prompt_includes_transcript_and_level():
    prompt = analysis_prompt(language="english", cefr_level="A2", transcript="user: Hi\nassistant: Hello")
    assert "A2" in prompt
    assert "user: Hi" in prompt
    assert '"vocab_suggestions"' in prompt


def test_learning_plan_prompt_includes_notes():
    prompt = learning_plan_prompt(language="english", cefr_level="A2", notes="struggled with past tense")
    assert "struggled with past tense" in prompt
    assert '"topics"' in prompt
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_prompts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tutor'`

- [ ] **Step 3: Implement `app/tutor/prompts.py`**

Create `backend/app/tutor/__init__.py` (empty file).

```python
from app.repositories.session_repo import ConversationTurn

TUTOR_PERSONA = (
    "You are a friendly, encouraging personal language tutor. You always respond "
    "only in {language}, adapting your vocabulary and grammar complexity to a "
    "{cefr_level} (CEFR) learner. When the learner makes a mistake, gently correct "
    "it within your reply and keep the conversation going. Keep replies short "
    "(2-4 sentences)."
)

PLAN_FOCUS_ADDENDUM = "Try to steer the conversation towards this topic/scenario: {topic}."


def tutor_system_prompt(*, language: str, cefr_level: str, plan_topic: str | None) -> str:
    prompt = TUTOR_PERSONA.format(language=language, cefr_level=cefr_level)
    if plan_topic:
        prompt += " " + PLAN_FOCUS_ADDENDUM.format(topic=plan_topic)
    return prompt


PLACEMENT_PERSONA = (
    "You are a language placement examiner for {language}. Ask the learner one "
    "question at a time, starting easy and increasing difficulty based on their "
    "answers, to estimate their CEFR level (A1-C2). Ask a maximum of 5 questions "
    "total. After the final question, once you have enough information, respond "
    'ONLY with a JSON object: {{"level": "A1"}} (use the estimated level, no '
    "other text). Otherwise, just ask the next question in {language}."
)


def placement_system_prompt(*, language: str) -> str:
    return PLACEMENT_PERSONA.format(language=language)


def build_chat_messages(
    *, system_prompt: str, history: list[ConversationTurn], user_message: str
) -> list[dict]:
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend({"role": turn.role, "content": turn.content} for turn in history)
    messages.append({"role": "user", "content": user_message})
    return messages


ANALYSIS_PERSONA = (
    "You are analyzing a {language} learner's practice conversation transcript "
    "below to update their profile. The learner's current level is {cefr_level}. "
    'Respond ONLY with a JSON object with these keys: '
    '"updated_level" (CEFR level string or null if unchanged), '
    '"notable_errors" (array of short strings), '
    '"vocab_suggestions" (array of objects with "term", "translation", '
    '"example_sentence"), "next_topics" (array of short topic strings).\n\n'
    "Transcript:\n{transcript}"
)


def analysis_prompt(*, language: str, cefr_level: str, transcript: str) -> str:
    return ANALYSIS_PERSONA.format(language=language, cefr_level=cefr_level, transcript=transcript)


LEARNING_PLAN_PERSONA = (
    "Create a short {language} learning plan for a {cefr_level} learner. "
    "Consider these recent notes: {notes}. Respond ONLY with a JSON object with "
    'key "topics": an array of 3-5 short dialog topic/scenario strings suited '
    "to their level."
)


def learning_plan_prompt(*, language: str, cefr_level: str, notes: str) -> str:
    return LEARNING_PLAN_PERSONA.format(language=language, cefr_level=cefr_level, notes=notes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_prompts.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tutor/__init__.py backend/app/tutor/prompts.py backend/tests/test_prompts.py
git commit -m "feat: add tutor prompt templates"
```

---

### Task 10: Dialog service (practice turn orchestration)

**Files:**
- Create: `backend/app/tutor/dialog_service.py`
- Test: `backend/tests/test_dialog_service.py`

**Interfaces:**
- Consumes: `OllamaClient` (Task 6), `session_repo.*` (Task 7), `learning_plan_repo.get_latest_plan` (Task 8), `tutor_system_prompt`/`build_chat_messages` (Task 9), `Profile` (Task 3).
- Produces: `send_practice_turn(conn, *, ollama: OllamaClient, profile: Profile, user_message: str) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_dialog_service.py
from unittest.mock import MagicMock

from app.repositories import session_repo
from app.repositories.learning_plan_repo import create_plan
from app.repositories.profile_repo import Profile
from app.tutor.dialog_service import send_practice_turn


def _fake_ollama(reply: str) -> MagicMock:
    client = MagicMock()
    client.chat.return_value = reply
    return client


def test_send_practice_turn_persists_user_and_assistant_turns(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    ollama = _fake_ollama("Hello there!")

    reply = send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Hi!")

    assert reply == "Hello there!"
    session_id = session_repo.get_active_session(conn, language="english", session_type="practice")
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert [(t.role, t.content) for t in turns] == [("user", "Hi!"), ("assistant", "Hello there!")]


def test_send_practice_turn_reuses_active_session(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    ollama = _fake_ollama("First reply")
    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Msg 1")

    ollama.chat.return_value = "Second reply"
    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Msg 2")

    session_id = session_repo.get_active_session(conn, language="english", session_type="practice")
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert len(turns) == 4


def test_send_practice_turn_includes_plan_topic_in_system_prompt(conn):
    profile = Profile(language="english", cefr_level="B1", created_at="now")
    create_plan(conn, language="english", topics=["Ordering food", "Small talk"])
    ollama = _fake_ollama("Sure, let's talk about food.")

    send_practice_turn(conn, ollama=ollama, profile=profile, user_message="Hi!")

    sent_messages = ollama.chat.call_args.args[0]
    assert "Ordering food" in sent_messages[0]["content"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_dialog_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tutor.dialog_service'`

- [ ] **Step 3: Implement `app/tutor/dialog_service.py`**

```python
from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo
from app.repositories.learning_plan_repo import get_latest_plan
from app.repositories.profile_repo import Profile
from app.tutor.prompts import build_chat_messages, tutor_system_prompt


def send_practice_turn(
    conn: Connection, *, ollama: OllamaClient, profile: Profile, user_message: str
) -> str:
    session_id = session_repo.get_active_session(
        conn, language=profile.language, session_type="practice"
    )
    if session_id is None:
        session_id = session_repo.create_session(
            conn, language=profile.language, session_type="practice"
        )

    plan = get_latest_plan(conn, language=profile.language)
    plan_topic = plan.topics[0] if plan and plan.topics else None

    system_prompt = tutor_system_prompt(
        language=profile.language, cefr_level=profile.cefr_level, plan_topic=plan_topic
    )
    history = session_repo.get_turns(conn, session_id=session_id)
    messages = build_chat_messages(system_prompt=system_prompt, history=history, user_message=user_message)

    assistant_text = ollama.chat(messages)

    session_repo.add_turn(conn, session_id=session_id, role="user", content=user_message)
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=assistant_text)

    return assistant_text
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_dialog_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tutor/dialog_service.py backend/tests/test_dialog_service.py
git commit -m "feat: add practice dialog turn orchestration service"
```

---

### Task 11: Placement service

**Files:**
- Create: `backend/app/tutor/placement_service.py`
- Test: `backend/tests/test_placement_service.py`

**Interfaces:**
- Consumes: `OllamaClient` (Task 6), `session_repo.*` (Task 7), `placement_system_prompt`/`build_chat_messages` (Task 9), `update_profile` (Task 3).
- Produces: `start_placement(conn, *, ollama, language: str) -> tuple[int, str]`. `continue_placement(conn, *, ollama, session_id: int, language: str, user_answer: str) -> tuple[bool, str]` — returns `(finished, question)` if not finished, or `(True, level)` if finished.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_placement_service.py
from unittest.mock import MagicMock

from app.repositories import session_repo
from app.repositories.profile_repo import get_or_create_profile
from app.tutor.placement_service import continue_placement, start_placement


def test_start_placement_creates_session_and_returns_first_question(conn):
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"

    session_id, question = start_placement(conn, ollama=ollama, language="english")

    assert question == "What is your name?"
    turns = session_repo.get_turns(conn, session_id=session_id)
    assert turns == [session_repo.ConversationTurn(role="assistant", content="What is your name?")]


def test_continue_placement_returns_next_question_when_not_finished(conn):
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"
    session_id, _ = start_placement(conn, ollama=ollama, language="english")

    ollama.chat.return_value = "How old are you?"
    finished, result = continue_placement(
        conn, ollama=ollama, session_id=session_id, language="english", user_answer="Anna"
    )

    assert finished is False
    assert result == "How old are you?"


def test_continue_placement_finalizes_level_when_llm_returns_json(conn):
    get_or_create_profile(conn, default_language="english")
    ollama = MagicMock()
    ollama.chat.return_value = "What is your name?"
    session_id, _ = start_placement(conn, ollama=ollama, language="english")

    ollama.chat.return_value = '{"level": "B1"}'
    finished, result = continue_placement(
        conn, ollama=ollama, session_id=session_id, language="english", user_answer="Anna, 30 years old"
    )

    assert finished is True
    assert result == "B1"
    profile = get_or_create_profile(conn, default_language="english")
    assert profile.cefr_level == "B1"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_placement_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tutor.placement_service'`

- [ ] **Step 3: Implement `app/tutor/placement_service.py`**

```python
import json
from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo
from app.repositories.profile_repo import update_profile
from app.tutor.prompts import build_chat_messages, placement_system_prompt


def start_placement(conn: Connection, *, ollama: OllamaClient, language: str) -> tuple[int, str]:
    session_id = session_repo.create_session(conn, language=language, session_type="placement")
    system_prompt = placement_system_prompt(language=language)
    first_question = ollama.chat([{"role": "system", "content": system_prompt}])
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=first_question)
    return session_id, first_question


def continue_placement(
    conn: Connection, *, ollama: OllamaClient, session_id: int, language: str, user_answer: str
) -> tuple[bool, str]:
    system_prompt = placement_system_prompt(language=language)
    history = session_repo.get_turns(conn, session_id=session_id)
    messages = build_chat_messages(system_prompt=system_prompt, history=history, user_message=user_answer)

    response = ollama.chat(messages)
    session_repo.add_turn(conn, session_id=session_id, role="user", content=user_answer)

    level = _parse_level(response)
    if level is not None:
        session_repo.add_turn(conn, session_id=session_id, role="assistant", content=response)
        session_repo.end_session(conn, session_id=session_id)
        update_profile(conn, cefr_level=level)
        return True, level

    session_repo.add_turn(conn, session_id=session_id, role="assistant", content=response)
    return False, response


def _parse_level(response: str) -> str | None:
    try:
        data = json.loads(response.strip())
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and "level" in data:
        return str(data["level"])
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_placement_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tutor/placement_service.py backend/tests/test_placement_service.py
git commit -m "feat: add CEFR placement dialog service"
```

---

### Task 12: Session analysis and learning-plan regeneration service

**Files:**
- Create: `backend/app/tutor/analysis_service.py`
- Test: `backend/tests/test_analysis_service.py`

**Interfaces:**
- Consumes: `OllamaClient` (Task 6), `session_repo.*` (Task 7), `vocab_repo.create_card` (Task 5), `learning_plan_repo.create_plan` (Task 8), `Profile`/`update_profile` (Task 3), `analysis_prompt`/`learning_plan_prompt` (Task 9).
- Produces: `analyze_session(conn, *, ollama, profile: Profile, session_id: int) -> dict` (keys: `updated_level`, `notable_errors`, `vocab_suggestions`, `next_topics`). `regenerate_learning_plan(conn, *, ollama, profile: Profile, notes: str) -> LearningPlan`.

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_analysis_service.py
import json
from unittest.mock import MagicMock

from app.repositories import session_repo, vocab_repo
from app.repositories.profile_repo import Profile, get_or_create_profile
from app.tutor.analysis_service import analyze_session, regenerate_learning_plan


def test_analyze_session_updates_profile_and_creates_vocab_cards(conn):
    get_or_create_profile(conn, default_language="english")
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    session_id = session_repo.create_session(conn, language="english", session_type="practice")
    session_repo.add_turn(conn, session_id=session_id, role="user", content="I go to shop yesterday.")
    session_repo.add_turn(conn, session_id=session_id, role="assistant", content="You mean 'I went to the shop yesterday'.")

    ollama = MagicMock()
    ollama.chat.return_value = json.dumps(
        {
            "updated_level": "B1",
            "notable_errors": ["past tense of 'go'"],
            "vocab_suggestions": [
                {"term": "shop", "translation": "Geschäft", "example_sentence": "I went to the shop."}
            ],
            "next_topics": ["Past tense practice"],
        }
    )

    analysis = analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)

    assert analysis["updated_level"] == "B1"
    updated_profile = get_or_create_profile(conn, default_language="english")
    assert updated_profile.cefr_level == "B1"
    due_cards = vocab_repo.get_due_cards(conn, language="english")
    assert [c.term for c in due_cards] == ["shop"]


def test_analyze_session_handles_malformed_llm_response(conn):
    get_or_create_profile(conn, default_language="english")
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    session_id = session_repo.create_session(conn, language="english", session_type="practice")

    ollama = MagicMock()
    ollama.chat.return_value = "not valid json"

    analysis = analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)

    assert analysis == {}
    unchanged_profile = get_or_create_profile(conn, default_language="english")
    assert unchanged_profile.cefr_level == "A2"


def test_regenerate_learning_plan_creates_plan_from_llm_topics(conn):
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    ollama = MagicMock()
    ollama.chat.return_value = json.dumps({"topics": ["Ordering food", "Asking for directions"]})

    plan = regenerate_learning_plan(conn, ollama=ollama, profile=profile, notes="struggled with past tense")

    assert plan.topics == ["Ordering food", "Asking for directions"]


def test_regenerate_learning_plan_falls_back_when_llm_response_has_no_topics(conn):
    profile = Profile(language="english", cefr_level="A2", created_at="now")
    ollama = MagicMock()
    ollama.chat.return_value = "not valid json"

    plan = regenerate_learning_plan(conn, ollama=ollama, profile=profile, notes="")

    assert plan.topics == ["General conversation practice"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_analysis_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.tutor.analysis_service'`

- [ ] **Step 3: Implement `app/tutor/analysis_service.py`**

```python
import json
from sqlite3 import Connection

from app.ollama_client import OllamaClient
from app.repositories import session_repo, vocab_repo
from app.repositories.learning_plan_repo import LearningPlan, create_plan
from app.repositories.profile_repo import Profile, update_profile
from app.tutor.prompts import analysis_prompt, learning_plan_prompt


def analyze_session(conn: Connection, *, ollama: OllamaClient, profile: Profile, session_id: int) -> dict:
    turns = session_repo.get_turns(conn, session_id=session_id)
    transcript = "\n".join(f"{turn.role}: {turn.content}" for turn in turns)

    prompt = analysis_prompt(language=profile.language, cefr_level=profile.cefr_level, transcript=transcript)
    response = ollama.chat([{"role": "system", "content": prompt}])
    analysis = _parse_json_object(response)

    if analysis.get("updated_level"):
        update_profile(conn, cefr_level=analysis["updated_level"])

    for suggestion in analysis.get("vocab_suggestions", []):
        vocab_repo.create_card(
            conn,
            language=profile.language,
            term=suggestion["term"],
            translation=suggestion["translation"],
            example_sentence=suggestion.get("example_sentence", ""),
            source_session_id=session_id,
        )

    conn.execute(
        """INSERT INTO session_analyses
           (session_id, updated_level, notable_errors_json, vocab_suggestions_json, next_topics_json, created_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))""",
        (
            session_id,
            analysis.get("updated_level"),
            json.dumps(analysis.get("notable_errors", [])),
            json.dumps(analysis.get("vocab_suggestions", [])),
            json.dumps(analysis.get("next_topics", [])),
        ),
    )
    conn.commit()

    return analysis


def regenerate_learning_plan(
    conn: Connection, *, ollama: OllamaClient, profile: Profile, notes: str
) -> LearningPlan:
    prompt = learning_plan_prompt(language=profile.language, cefr_level=profile.cefr_level, notes=notes)
    response = ollama.chat([{"role": "system", "content": prompt}])
    data = _parse_json_object(response)
    topics = data.get("topics") or ["General conversation practice"]
    return create_plan(conn, language=profile.language, topics=topics)


def _parse_json_object(response: str) -> dict:
    try:
        data = json.loads(response.strip())
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_analysis_service.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/tutor/analysis_service.py backend/tests/test_analysis_service.py
git commit -m "feat: add session analysis and learning-plan regeneration service"
```

---

### Task 13: FastAPI endpoints

**Files:**
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/schemas.py`
- Create: `backend/app/dependencies.py`
- Create: `backend/app/api/routes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_routes.py`

**Interfaces:**
- Consumes: everything from Tasks 3–12.
- Produces: HTTP API — `GET /api/profile`, `POST /api/dialog/practice`, `POST /api/dialog/placement/start`, `POST /api/dialog/placement/answer`, `GET /api/learning-plan`, `POST /api/session/{session_id}/analyze`, `GET /api/vocab/due`, `POST /api/vocab/answer`.

- [ ] **Step 1: Write the failing route tests**

```python
# backend/tests/test_routes.py
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db, get_ollama
from app.main import app
from app.repositories import vocab_repo


@pytest.fixture
def client(conn):
    fake_ollama = MagicMock()

    def override_get_db():
        yield conn

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ollama] = lambda: fake_ollama
    test_client = TestClient(app)
    test_client.fake_ollama = fake_ollama
    yield test_client
    app.dependency_overrides.clear()


def test_get_profile_creates_default_profile(client):
    response = client.get("/api/profile")
    assert response.status_code == 200
    assert response.json() == {"language": "english", "cefr_level": "UNPLACED"}


def test_practice_turn_returns_reply(client):
    client.fake_ollama.chat.return_value = "Hello there!"
    response = client.post("/api/dialog/practice", json={"message": "Hi!"})
    assert response.status_code == 200
    assert response.json() == {"reply": "Hello there!"}


def test_placement_start_and_answer_flow(client):
    client.fake_ollama.chat.return_value = "What is your name?"
    start_response = client.post("/api/dialog/placement/start")
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]
    assert start_response.json()["question"] == "What is your name?"

    client.fake_ollama.chat.return_value = '{"level": "B1"}'
    answer_response = client.post(
        "/api/dialog/placement/answer", json={"session_id": session_id, "answer": "Anna"}
    )
    assert answer_response.status_code == 200
    assert answer_response.json() == {"finished": True, "question": None, "level": "B1"}


def test_learning_plan_returns_404_when_none_exists(client):
    response = client.get("/api/learning-plan")
    assert response.status_code == 404


def test_vocab_due_and_answer_flow(client, conn):
    card = vocab_repo.create_card(
        conn, language="english", term="house", translation="Haus", example_sentence="x"
    )

    due_response = client.get("/api/vocab/due")
    assert due_response.status_code == 200
    assert due_response.json()[0]["term"] == "house"

    answer_response = client.post("/api/vocab/answer", json={"card_id": card.id, "answer": "Haus"})
    assert answer_response.status_code == 200
    assert answer_response.json() == {"correct": True}


def test_vocab_answer_returns_404_for_unknown_card(client):
    response = client.post("/api/vocab/answer", json={"card_id": 999, "answer": "x"})
    assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_routes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.dependencies'`

- [ ] **Step 3: Implement `app/dependencies.py`**

```python
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
```

- [ ] **Step 4: Implement `app/api/schemas.py`**

Create `backend/app/api/__init__.py` (empty file).

```python
from pydantic import BaseModel


class ProfileResponse(BaseModel):
    language: str
    cefr_level: str


class PracticeTurnRequest(BaseModel):
    message: str


class PracticeTurnResponse(BaseModel):
    reply: str


class PlacementStartResponse(BaseModel):
    session_id: int
    question: str


class PlacementAnswerRequest(BaseModel):
    session_id: int
    answer: str


class PlacementAnswerResponse(BaseModel):
    finished: bool
    question: str | None = None
    level: str | None = None


class LearningPlanResponse(BaseModel):
    topics: list[str]


class VocabCardResponse(BaseModel):
    id: int
    term: str
    translation: str
    example_sentence: str
    due_date: str


class VocabAnswerRequest(BaseModel):
    card_id: int
    answer: str


class VocabAnswerResponse(BaseModel):
    correct: bool


class AnalyzeSessionResponse(BaseModel):
    updated_level: str | None = None
    notable_errors: list[str] = []
    vocab_suggestions: list[dict] = []
    next_topics: list[str] = []
```

- [ ] **Step 5: Implement `app/api/routes.py`**

```python
from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    AnalyzeSessionResponse,
    LearningPlanResponse,
    PlacementAnswerRequest,
    PlacementAnswerResponse,
    PlacementStartResponse,
    PracticeTurnRequest,
    PracticeTurnResponse,
    ProfileResponse,
    VocabAnswerRequest,
    VocabAnswerResponse,
    VocabCardResponse,
)
from app.config import settings
from app.dependencies import get_db, get_ollama
from app.ollama_client import OllamaClient
from app.repositories import vocab_repo
from app.repositories.learning_plan_repo import get_latest_plan
from app.repositories.profile_repo import get_or_create_profile
from app.srs import vocab_service
from app.tutor import analysis_service, dialog_service, placement_service

router = APIRouter(prefix="/api")


@router.get("/profile", response_model=ProfileResponse)
def read_profile(conn: Connection = Depends(get_db)) -> ProfileResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    return ProfileResponse(language=profile.language, cefr_level=profile.cefr_level)


@router.post("/dialog/practice", response_model=PracticeTurnResponse)
def practice_turn(
    body: PracticeTurnRequest,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PracticeTurnResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    reply = dialog_service.send_practice_turn(conn, ollama=ollama, profile=profile, user_message=body.message)
    return PracticeTurnResponse(reply=reply)


@router.post("/dialog/placement/start", response_model=PlacementStartResponse)
def placement_start(
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PlacementStartResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    session_id, question = placement_service.start_placement(conn, ollama=ollama, language=profile.language)
    return PlacementStartResponse(session_id=session_id, question=question)


@router.post("/dialog/placement/answer", response_model=PlacementAnswerResponse)
def placement_answer(
    body: PlacementAnswerRequest,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PlacementAnswerResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    finished, result = placement_service.continue_placement(
        conn, ollama=ollama, session_id=body.session_id, language=profile.language, user_answer=body.answer
    )
    if finished:
        return PlacementAnswerResponse(finished=True, level=result)
    return PlacementAnswerResponse(finished=False, question=result)


@router.get("/learning-plan", response_model=LearningPlanResponse)
def read_learning_plan(conn: Connection = Depends(get_db)) -> LearningPlanResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    plan = get_latest_plan(conn, language=profile.language)
    if plan is None:
        raise HTTPException(status_code=404, detail="No learning plan yet")
    return LearningPlanResponse(topics=plan.topics)


@router.post("/session/{session_id}/analyze", response_model=AnalyzeSessionResponse)
def analyze_session_endpoint(
    session_id: int,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> AnalyzeSessionResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    analysis = analysis_service.analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)
    return AnalyzeSessionResponse(
        updated_level=analysis.get("updated_level"),
        notable_errors=analysis.get("notable_errors", []),
        vocab_suggestions=analysis.get("vocab_suggestions", []),
        next_topics=analysis.get("next_topics", []),
    )


@router.get("/vocab/due", response_model=list[VocabCardResponse])
def read_due_cards(conn: Connection = Depends(get_db)) -> list[VocabCardResponse]:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    cards = vocab_repo.get_due_cards(conn, language=profile.language)
    return [
        VocabCardResponse(
            id=c.id, term=c.term, translation=c.translation,
            example_sentence=c.example_sentence, due_date=c.due_date,
        )
        for c in cards
    ]


@router.post("/vocab/answer", response_model=VocabAnswerResponse)
def answer_vocab_card(
    body: VocabAnswerRequest,
    conn: Connection = Depends(get_db),
) -> VocabAnswerResponse:
    card = vocab_repo.get_card_by_id(conn, card_id=body.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    correct = vocab_service.submit_answer(conn, card=card, user_answer=body.answer)
    return VocabAnswerResponse(correct=correct)
```

- [ ] **Step 6: Wire the router into the app**

Update `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import settings
from app.db import init_db

app = FastAPI(title="Speaker Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db(settings.db_path)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && . .venv/bin/activate && python -m pytest tests/test_routes.py -v`
Expected: PASS (6 passed)

- [ ] **Step 8: Run the full backend test suite**

Run: `cd backend && . .venv/bin/activate && python -m pytest -v`
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add backend/app/api backend/app/dependencies.py backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: wire up FastAPI endpoints for dialog, placement, learning plan, and vocab"
```

---

## Frontend

### Task 14: Frontend scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/App.test.tsx`
- Create: `frontend/src/setupTests.ts`
- Create: `frontend/src/api.ts`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Modify: `docker-compose.yml`

**Interfaces:**
- Produces: `App` component (default export from `src/App.tsx`). `API_BASE_URL` constant and `getProfile(): Promise<{language: string; cefr_level: string}>` in `src/api.ts`.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "speaker-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.5.0",
    "@testing-library/react": "^16.0.1",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "jsdom": "^25.0.0",
    "typescript": "^5.5.4",
    "vite": "^5.4.2",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.ts`**

```ts
/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
  },
});
```

- [ ] **Step 3: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="de">
  <head>
    <meta charset="UTF-8" />
    <title>Speaker</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/src/setupTests.ts`**

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 6: Create `frontend/src/api.ts`**

```ts
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export interface ProfileResponse {
  language: string;
  cefr_level: string;
}

export async function getProfile(): Promise<ProfileResponse> {
  const response = await fetch(`${API_BASE_URL}/api/profile`);
  if (!response.ok) {
    throw new Error(`Failed to fetch profile: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 7: Install dependencies**

Run: `cd frontend && npm install`
Expected: installs without errors, creates `package-lock.json` and `node_modules/`.

- [ ] **Step 8: Write the failing test**

```tsx
// frontend/src/App.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "./App";

describe("App", () => {
  it("renders the app title", () => {
    render(<App />);
    expect(screen.getByText("Speaker")).toBeInTheDocument();
  });
});
```

- [ ] **Step 9: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: FAIL — cannot find module `./App`

- [ ] **Step 10: Implement `frontend/src/App.tsx`**

```tsx
export default function App() {
  return (
    <div>
      <h1>Speaker</h1>
      <p>Dein persönlicher Sprachlehrer.</p>
    </div>
  );
}
```

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 11: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/App.test.tsx`
Expected: PASS (1 passed)

- [ ] **Step 12: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 13: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

- [ ] **Step 14: Add the frontend service to `docker-compose.yml`**

Add this service to the `services:` section (after `backend`), and keep the existing `ollama`, `backend`, and `volumes` sections unchanged:

```yaml
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

- [ ] **Step 15: Verify the frontend container builds**

Run:
```bash
docker compose build frontend
docker compose up -d frontend
curl -sf http://localhost:3000 | grep -q "Speaker"
docker compose down
```
Expected: no build errors, curl finds "Speaker" in the served HTML.

- [ ] **Step 16: Commit**

```bash
git add frontend docker-compose.yml
git commit -m "feat: add frontend scaffolding with Vite/React/TS and nginx Docker build"
```

---

### Task 15: Frontend chat/dialog UI

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/ChatView.tsx`
- Create: `frontend/src/ChatView.test.tsx`
- Modify: `frontend/src/App.tsx`

**Interfaces:**
- Consumes: `API_BASE_URL`, `getProfile` (Task 14).
- Produces: `ChatMessage` type in `src/types.ts`. `sendPracticeTurn(message: string): Promise<{reply: string}>`, `startPlacement(): Promise<{session_id: number; question: string}>`, `answerPlacement(sessionId: number, answer: string): Promise<{finished: boolean; question?: string; level?: string}>` added to `src/api.ts`. `ChatView` default export component.

- [ ] **Step 1: Create `frontend/src/types.ts`**

```ts
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}
```

- [ ] **Step 2: Add dialog API functions to `frontend/src/api.ts`**

Append to `frontend/src/api.ts`:

```ts
export interface PracticeTurnResponse {
  reply: string;
}

export async function sendPracticeTurn(message: string): Promise<PracticeTurnResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/practice`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error(`Failed to send turn: ${response.status}`);
  }
  return response.json();
}

export interface PlacementStartResponse {
  session_id: number;
  question: string;
}

export async function startPlacement(): Promise<PlacementStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/placement/start`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to start placement: ${response.status}`);
  }
  return response.json();
}

export interface PlacementAnswerResponse {
  finished: boolean;
  question?: string;
  level?: string;
}

export async function answerPlacement(
  sessionId: number,
  answer: string,
): Promise<PlacementAnswerResponse> {
  const response = await fetch(`${API_BASE_URL}/api/dialog/placement/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, answer }),
  });
  if (!response.ok) {
    throw new Error(`Failed to answer placement: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 3: Write the failing tests**

```tsx
// frontend/src/ChatView.test.tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChatView from "./ChatView";
import * as api from "./api";

vi.mock("./api");

describe("ChatView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("starts a placement dialog when the profile is unplaced", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.startPlacement).mockResolvedValue({ session_id: 1, question: "What is your name?" });

    render(<ChatView />);

    await waitFor(() => {
      expect(screen.getByText("What is your name?")).toBeInTheDocument();
    });
  });

  it("sends placement answers and shows the next question", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.startPlacement).mockResolvedValue({ session_id: 1, question: "What is your name?" });
    vi.mocked(api.answerPlacement).mockResolvedValue({ finished: false, question: "How old are you?" });

    render(<ChatView />);
    await waitFor(() => screen.getByText("What is your name?"));

    fireEvent.change(screen.getByPlaceholderText("Deine Nachricht..."), { target: { value: "Anna" } });
    fireEvent.click(screen.getByText("Senden"));

    await waitFor(() => {
      expect(screen.getByText("How old are you?")).toBeInTheDocument();
    });
    expect(api.answerPlacement).toHaveBeenCalledWith(1, "Anna");
  });

  it("uses practice mode directly when a level is already set", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "B1" });
    vi.mocked(api.sendPracticeTurn).mockResolvedValue({ reply: "Nice to meet you!" });

    render(<ChatView />);
    await waitFor(() => expect(api.getProfile).toHaveBeenCalled());

    fireEvent.change(screen.getByPlaceholderText("Deine Nachricht..."), { target: { value: "Hi there" } });
    fireEvent.click(screen.getByText("Senden"));

    await waitFor(() => {
      expect(screen.getByText("Nice to meet you!")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/ChatView.test.tsx`
Expected: FAIL — cannot find module `./ChatView`

- [ ] **Step 5: Implement `frontend/src/ChatView.tsx`**

```tsx
import { useEffect, useState } from "react";
import { answerPlacement, getProfile, sendPracticeTurn, startPlacement } from "./api";
import type { ChatMessage } from "./types";

type Mode = "loading" | "placement" | "practice";

export default function ChatView() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("loading");
  const [placementSessionId, setPlacementSessionId] = useState<number | null>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    getProfile().then((profile) => {
      if (profile.cefr_level === "UNPLACED") {
        startPlacement().then((res) => {
          setPlacementSessionId(res.session_id);
          setMessages([{ role: "assistant", content: res.question }]);
          setMode("placement");
        });
      } else {
        setMode("practice");
      }
    });
  }, []);

  async function handleSend() {
    if (!input.trim() || sending) return;
    const userMessage = input.trim();
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setInput("");
    setSending(true);
    try {
      if (mode === "placement" && placementSessionId !== null) {
        const res = await answerPlacement(placementSessionId, userMessage);
        if (res.finished) {
          setMessages((prev) => [...prev, { role: "assistant", content: `Dein Level: ${res.level}` }]);
          setMode("practice");
        } else if (res.question) {
          setMessages((prev) => [...prev, { role: "assistant", content: res.question! }]);
        }
      } else {
        const res = await sendPracticeTurn(userMessage);
        setMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      }
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <div data-testid="messages">
        {messages.map((m, i) => (
          <p key={i} data-role={m.role}>
            {m.content}
          </p>
        ))}
      </div>
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSend();
        }}
        placeholder="Deine Nachricht..."
        disabled={mode === "loading" || sending}
      />
      <button onClick={handleSend} disabled={mode === "loading" || sending}>
        Senden
      </button>
    </div>
  );
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/ChatView.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 7: Wire `ChatView` into `App.tsx`**

Update `frontend/src/App.tsx`:

```tsx
import ChatView from "./ChatView";

export default function App() {
  return (
    <div>
      <h1>Speaker</h1>
      <ChatView />
    </div>
  );
}
```

Note: `App.test.tsx` still passes because it only checks for the text "Speaker", which remains present.

- [ ] **Step 8: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api.ts frontend/src/types.ts frontend/src/ChatView.tsx frontend/src/ChatView.test.tsx frontend/src/App.tsx
git commit -m "feat: add chat dialog UI with placement and practice modes"
```

---

### Task 16: Frontend vocabulary flashcard UI

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/VocabView.tsx`
- Create: `frontend/src/VocabView.test.tsx`

**Interfaces:**
- Consumes: `API_BASE_URL` (Task 14).
- Produces: `VocabCard` interface, `getDueCards(): Promise<VocabCard[]>`, `answerVocabCard(cardId: number, answer: string): Promise<{correct: boolean}>` added to `src/api.ts`. `VocabView` default export component.

- [ ] **Step 1: Add vocab API functions to `frontend/src/api.ts`**

Append to `frontend/src/api.ts`:

```ts
export interface VocabCard {
  id: number;
  term: string;
  translation: string;
  example_sentence: string;
  due_date: string;
}

export async function getDueCards(): Promise<VocabCard[]> {
  const response = await fetch(`${API_BASE_URL}/api/vocab/due`);
  if (!response.ok) {
    throw new Error(`Failed to fetch due cards: ${response.status}`);
  }
  return response.json();
}

export async function answerVocabCard(cardId: number, answer: string): Promise<{ correct: boolean }> {
  const response = await fetch(`${API_BASE_URL}/api/vocab/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ card_id: cardId, answer }),
  });
  if (!response.ok) {
    throw new Error(`Failed to submit answer: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Write the failing tests**

```tsx
// frontend/src/VocabView.test.tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VocabView from "./VocabView";
import * as api from "./api";

vi.mock("./api");

describe("VocabView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows a message when no cards are due", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([]);

    render(<VocabView />);

    await waitFor(() => {
      expect(screen.getByText("Keine fälligen Karteikarten.")).toBeInTheDocument();
    });
  });

  it("shows the term, then feedback after submitting an answer", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([
      { id: 1, term: "house", translation: "Haus", example_sentence: "x", due_date: "2026-07-21" },
    ]);
    vi.mocked(api.answerVocabCard).mockResolvedValue({ correct: true });

    render(<VocabView />);
    await waitFor(() => screen.getByText("house"));

    fireEvent.change(screen.getByPlaceholderText("Übersetzung eingeben..."), {
      target: { value: "Haus" },
    });
    fireEvent.click(screen.getByText("Prüfen"));

    await waitFor(() => {
      expect(screen.getByText("Richtig!")).toBeInTheDocument();
    });
    expect(api.answerVocabCard).toHaveBeenCalledWith(1, "Haus");
  });

  it("shows the correct translation and advances after an incorrect answer", async () => {
    vi.mocked(api.getDueCards).mockResolvedValue([
      { id: 1, term: "house", translation: "Haus", example_sentence: "x", due_date: "2026-07-21" },
    ]);
    vi.mocked(api.answerVocabCard).mockResolvedValue({ correct: false });

    render(<VocabView />);
    await waitFor(() => screen.getByText("house"));

    fireEvent.change(screen.getByPlaceholderText("Übersetzung eingeben..."), {
      target: { value: "Katze" },
    });
    fireEvent.click(screen.getByText("Prüfen"));

    await waitFor(() => {
      expect(screen.getByText("Falsch. Richtig wäre: Haus")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Weiter"));
    expect(screen.getByText("Alle fälligen Karten erledigt!")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/VocabView.test.tsx`
Expected: FAIL — cannot find module `./VocabView`

- [ ] **Step 4: Implement `frontend/src/VocabView.tsx`**

```tsx
import { useEffect, useState } from "react";
import { answerVocabCard, getDueCards } from "./api";
import type { VocabCard } from "./api";

export default function VocabView() {
  const [cards, setCards] = useState<VocabCard[]>([]);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<"correct" | "incorrect" | null>(null);

  useEffect(() => {
    getDueCards().then(setCards);
  }, []);

  const currentCard = cards[index];

  async function handleSubmit() {
    if (!currentCard) return;
    const result = await answerVocabCard(currentCard.id, answer);
    setFeedback(result.correct ? "correct" : "incorrect");
  }

  function handleNext() {
    setFeedback(null);
    setAnswer("");
    setIndex((i) => i + 1);
  }

  if (cards.length === 0) {
    return <p>Keine fälligen Karteikarten.</p>;
  }

  if (!currentCard) {
    return <p>Alle fälligen Karten erledigt!</p>;
  }

  return (
    <div>
      <p>{currentCard.term}</p>
      {feedback === null ? (
        <>
          <input
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Übersetzung eingeben..."
          />
          <button onClick={handleSubmit}>Prüfen</button>
        </>
      ) : (
        <>
          <p>{feedback === "correct" ? "Richtig!" : `Falsch. Richtig wäre: ${currentCard.translation}`}</p>
          <button onClick={handleNext}>Weiter</button>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/VocabView.test.tsx`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api.ts frontend/src/VocabView.tsx frontend/src/VocabView.test.tsx
git commit -m "feat: add vocabulary flashcard quiz UI"
```

---

### Task 17: Frontend learning-plan/profile view and navigation

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/ProfileView.tsx`
- Create: `frontend/src/ProfileView.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: `API_BASE_URL`, `getProfile` (Task 14), `ChatView` (Task 15), `VocabView` (Task 16).
- Produces: `getLearningPlan(): Promise<{topics: string[]} | null>` added to `src/api.ts`. `ProfileView` default export component. `App` now renders a tab navigation between Dialog/Vokabeln/Profil.

- [ ] **Step 1: Add learning-plan API function to `frontend/src/api.ts`**

Append to `frontend/src/api.ts`:

```ts
export interface LearningPlanResponse {
  topics: string[];
}

export async function getLearningPlan(): Promise<LearningPlanResponse | null> {
  const response = await fetch(`${API_BASE_URL}/api/learning-plan`);
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Failed to fetch learning plan: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 2: Write the failing tests**

```tsx
// frontend/src/ProfileView.test.tsx
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ProfileView from "./ProfileView";
import * as api from "./api";

vi.mock("./api");

describe("ProfileView", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("shows the current level and learning plan topics", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "B1" });
    vi.mocked(api.getLearningPlan).mockResolvedValue({ topics: ["Ordering food", "Small talk"] });

    render(<ProfileView />);

    await waitFor(() => {
      expect(screen.getByText("Aktuelles Level: B1")).toBeInTheDocument();
    });
    expect(screen.getByText("Ordering food")).toBeInTheDocument();
    expect(screen.getByText("Small talk")).toBeInTheDocument();
  });

  it("shows a placeholder when no learning plan exists yet", async () => {
    vi.mocked(api.getProfile).mockResolvedValue({ language: "english", cefr_level: "UNPLACED" });
    vi.mocked(api.getLearningPlan).mockResolvedValue(null);

    render(<ProfileView />);

    await waitFor(() => {
      expect(screen.getByText("Noch kein Lernplan vorhanden.")).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/ProfileView.test.tsx`
Expected: FAIL — cannot find module `./ProfileView`

- [ ] **Step 4: Implement `frontend/src/ProfileView.tsx`**

```tsx
import { useEffect, useState } from "react";
import { getLearningPlan, getProfile } from "./api";

export default function ProfileView() {
  const [level, setLevel] = useState<string | null>(null);
  const [topics, setTopics] = useState<string[]>([]);

  useEffect(() => {
    getProfile().then((profile) => setLevel(profile.cefr_level));
    getLearningPlan().then((plan) => setTopics(plan?.topics ?? []));
  }, []);

  return (
    <div>
      <p>Aktuelles Level: {level ?? "wird ermittelt..."}</p>
      <h2>Aktueller Lernplan</h2>
      {topics.length === 0 ? (
        <p>Noch kein Lernplan vorhanden.</p>
      ) : (
        <ul>
          {topics.map((topic) => (
            <li key={topic}>{topic}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/ProfileView.test.tsx`
Expected: PASS (2 passed)

- [ ] **Step 6: Rewrite `App.tsx` with tab navigation**

```tsx
import { useState } from "react";
import ChatView from "./ChatView";
import ProfileView from "./ProfileView";
import VocabView from "./VocabView";

type Tab = "chat" | "vocab" | "profile";

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");

  return (
    <div>
      <h1>Speaker</h1>
      <nav>
        <button onClick={() => setTab("chat")}>Dialog</button>
        <button onClick={() => setTab("vocab")}>Vokabeln</button>
        <button onClick={() => setTab("profile")}>Profil</button>
      </nav>
      {tab === "chat" && <ChatView />}
      {tab === "vocab" && <VocabView />}
      {tab === "profile" && <ProfileView />}
    </div>
  );
}
```

- [ ] **Step 7: Rewrite `App.test.tsx` to test tab navigation**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./ChatView", () => ({ default: () => <div>ChatView</div> }));
vi.mock("./VocabView", () => ({ default: () => <div>VocabView</div> }));
vi.mock("./ProfileView", () => ({ default: () => <div>ProfileView</div> }));

describe("App", () => {
  it("shows the chat view by default and switches tabs", () => {
    render(<App />);
    expect(screen.getByText("ChatView")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Vokabeln"));
    expect(screen.getByText("VocabView")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Profil"));
    expect(screen.getByText("ProfileView")).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run the full frontend test suite**

Run: `cd frontend && npx vitest run`
Expected: all tests PASS

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api.ts frontend/src/ProfileView.tsx frontend/src/ProfileView.test.tsx frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "feat: add learning-plan/profile view and tab navigation"
```

---

## Deployment

### Task 18: Full docker-compose wiring, Ollama auto-pull, and end-to-end smoke test

**Files:**
- Modify: `docker-compose.yml`
- Create: `scripts/smoke_test.sh`

**Interfaces:**
- Consumes: all backend and frontend containers built in Tasks 1–17.
- Produces: a fully wired `docker-compose.yml` (ollama, ollama-init, backend, frontend) and an executable smoke-test script.

- [ ] **Step 1: Add the `ollama-init` service to `docker-compose.yml`**

Update `docker-compose.yml` to the following full content:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

  ollama-init:
    image: ollama/ollama:latest
    depends_on:
      - ollama
    environment:
      - OLLAMA_HOST=http://ollama:11434
    entrypoint: ["/bin/sh", "-c", "until ollama list >/dev/null 2>&1; do sleep 2; done; ollama pull ${OLLAMA_MODEL:-llama3.2:3b}"]
    restart: "no"

  backend:
    build: ./backend
    environment:
      - OLLAMA_HOST=http://ollama:11434
      - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2:3b}
      - DB_PATH=/data/speaker.db
      - DEFAULT_LANGUAGE=english
    volumes:
      - backend_data:/data
    ports:
      - "8000:8000"
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend

volumes:
  ollama_data:
  backend_data:
```

- [ ] **Step 2: Create `scripts/smoke_test.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Checking backend health..."
curl --fail --silent "$BASE_URL/api/health" | grep -q '"status":"ok"'

echo "Checking profile endpoint..."
curl --fail --silent "$BASE_URL/api/profile" | grep -q '"language"'

echo "Sending a practice dialog turn (requires a pulled Ollama model)..."
curl --fail --silent -X POST "$BASE_URL/api/dialog/practice" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | grep -q '"reply"'

echo "Smoke test passed."
```

Run: `chmod +x scripts/smoke_test.sh`

- [ ] **Step 3: Bring up the full stack and wait for the model pull**

Run:
```bash
docker compose up -d --build
docker compose logs -f ollama-init
```
Expected: log output ends with a completed pull (e.g. `success`) and the `ollama-init` container exits with code 0. This can take several minutes on first run depending on network speed — press Ctrl+C once you see the pull complete.

- [ ] **Step 4: Run the smoke test against the running stack**

Run: `./scripts/smoke_test.sh`
Expected:
```
Checking backend health...
Checking profile endpoint...
Sending a practice dialog turn (requires a pulled Ollama model)...
Smoke test passed.
```

- [ ] **Step 5: Tear down**

Run: `docker compose down`
Expected: all containers stop and are removed; named volumes (`ollama_data`, `backend_data`) persist for next start.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml scripts/smoke_test.sh
git commit -m "feat: wire up Ollama model auto-pull and add end-to-end smoke test"
```

---

## Self-Review Notes

- **Spec coverage:** Dialog flow (§5) → Tasks 9–10; proficiency/placement (§6) → Tasks 11–12; learning plan (§6) → Tasks 8, 12; flashcards/SRS (§7) → Tasks 4–5, 16; datamodel (§4) → Task 2; deployment (§8) → Tasks 1, 14, 18; testing (§9) → every task's own test step plus Task 18's smoke test. No spec section from the design doc is without a task.
- **Placeholder scan:** no TBD/TODO markers; every step contains complete, runnable code.
- **Type consistency:** `Profile`, `ConversationTurn`, `LearningPlan`, `VocabCard`, `SM2Result` field names and the function signatures that consume them (`send_practice_turn`, `continue_placement`, `analyze_session`, `submit_answer`, etc.) were kept identical across all tasks that reference them.
