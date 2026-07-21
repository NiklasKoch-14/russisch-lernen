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
