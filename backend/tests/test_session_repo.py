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
