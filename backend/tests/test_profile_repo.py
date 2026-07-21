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
