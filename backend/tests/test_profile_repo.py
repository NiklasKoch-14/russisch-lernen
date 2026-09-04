from app.repositories import profile_repo
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


def test_profile_defaults_show_transliteration_on(conn):
    profile = profile_repo.get_or_create_profile(conn, default_language="russian")
    assert profile.show_transliteration is True
    assert profile.placement_unit is None


def test_update_profile_toggles_transliteration(conn):
    profile_repo.get_or_create_profile(conn, default_language="russian")
    updated = profile_repo.update_profile(conn, show_transliteration=False)
    assert updated.show_transliteration is False
    assert profile_repo.get_or_create_profile(conn, "russian").show_transliteration is False


def test_update_profile_stores_placement_unit(conn):
    profile_repo.get_or_create_profile(conn, default_language="russian")
    assert profile_repo.update_profile(conn, placement_unit=7).placement_unit == 7
