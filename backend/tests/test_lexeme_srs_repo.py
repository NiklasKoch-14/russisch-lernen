from app.repositories import lexeme_srs_repo
from app.repositories.lexeme_srs_repo import SrsState


def _state(lexeme_id="delat", form_key="prs.1sg", due_date="2026-09-01") -> SrsState:
    return SrsState(
        lexeme_id=lexeme_id,
        form_key=form_key,
        interval_days=1.0,
        ease_factor=2.5,
        repetitions=1,
        due_date=due_date,
    )


def test_get_state_returns_none_when_unknown(conn):
    assert lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg") is None


def test_upsert_then_get_round_trips(conn):
    lexeme_srs_repo.upsert_state(conn, _state())
    assert lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg") == _state()


def test_upsert_replaces_existing_state(conn):
    lexeme_srs_repo.upsert_state(conn, _state())
    lexeme_srs_repo.upsert_state(conn, _state(due_date="2026-12-24"))
    stored = lexeme_srs_repo.get_state(conn, lexeme_id="delat", form_key="prs.1sg")
    assert stored.due_date == "2026-12-24"


def test_forms_of_same_lexeme_are_tracked_separately(conn):
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.1sg"))
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.3sg"))
    assert len(lexeme_srs_repo.due_states(conn, today="2026-09-02")) == 2


def test_due_states_excludes_future_dates(conn):
    lexeme_srs_repo.upsert_state(conn, _state(due_date="2026-09-01"))
    lexeme_srs_repo.upsert_state(conn, _state(form_key="prs.3sg", due_date="2026-09-30"))
    due = lexeme_srs_repo.due_states(conn, today="2026-09-02")
    assert [state.form_key for state in due] == ["prs.1sg"]


def test_due_states_respects_limit(conn):
    for index in range(5):
        lexeme_srs_repo.upsert_state(conn, _state(lexeme_id=f"l{index}"))
    assert len(lexeme_srs_repo.due_states(conn, today="2026-09-02", limit=3)) == 3
