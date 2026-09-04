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
    assert response.json() == {
        "language": "russian",
        "cefr_level": "UNPLACED",
        "show_transliteration": True,
        "placement_unit": None,
    }


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
        conn, language="russian", term="дом", translation="Haus", example_sentence="Это дом."
    )

    due_response = client.get("/api/vocab/due")
    assert due_response.status_code == 200
    assert due_response.json()[0]["term"] == "дом"

    answer_response = client.post("/api/vocab/answer", json={"card_id": card.id, "answer": "Haus"})
    assert answer_response.status_code == 200
    assert answer_response.json() == {"correct": True}


def test_vocab_answer_returns_404_for_unknown_card(client):
    response = client.post("/api/vocab/answer", json={"card_id": 999, "answer": "x"})
    assert response.status_code == 404
