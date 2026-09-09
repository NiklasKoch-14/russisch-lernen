from app.repositories import game_repo


def test_last_played_is_empty_initially(conn):
    assert game_repo.last_played(conn) == {}


def test_records_a_run_and_reports_its_time(conn):
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    assert game_repo.last_played(conn) == {"bar-01": "2026-09-08T10:00:00"}


def test_keeps_only_the_most_recent_time_per_scene(conn):
    game_repo.record_run(conn, scene_id="bar-01", seed="s1", played_at="2026-09-08T10:00:00")
    game_repo.record_run(conn, scene_id="bar-01", seed="s2", played_at="2026-09-09T10:00:00")
    assert game_repo.last_played(conn)["bar-01"] == "2026-09-09T10:00:00"
