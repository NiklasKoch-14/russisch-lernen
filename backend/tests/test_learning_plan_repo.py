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
