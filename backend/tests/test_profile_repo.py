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


def test_autoplay_is_on_by_default(conn):
    profile = get_or_create_profile(conn, default_language="russian")
    assert profile.audio_autoplay is True


def test_autoplay_can_be_switched_off(conn):
    get_or_create_profile(conn, default_language="russian")
    updated = update_profile(conn, audio_autoplay=False)
    assert updated.audio_autoplay is False
    assert get_or_create_profile(conn, default_language="russian").audio_autoplay is False


def test_autoplay_survives_unrelated_updates(conn):
    get_or_create_profile(conn, default_language="russian")
    update_profile(conn, audio_autoplay=False)
    update_profile(conn, show_transliteration=False)
    assert get_or_create_profile(conn, default_language="russian").audio_autoplay is False


def test_profile_defaults_to_typing_in_the_village(conn):
    profile = profile_repo.get_or_create_profile(conn, default_language="russian")
    assert profile.type_in_village is True


def test_update_profile_switches_back_to_tiles(conn):
    profile_repo.get_or_create_profile(conn, default_language="russian")
    updated = profile_repo.update_profile(conn, type_in_village=False)
    assert updated.type_in_village is False
    assert profile_repo.get_or_create_profile(conn, "russian").type_in_village is False
