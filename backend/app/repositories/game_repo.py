from sqlite3 import Connection


def record_run(conn: Connection, *, scene_id: str, seed: str, played_at: str) -> None:
    """Vermerken, dass eine Szene gespielt wurde — Grundlage der Szenenauswahl."""
    conn.execute(
        "INSERT INTO game_scene_runs (scene_id, seed, played_at) VALUES (?, ?, ?)",
        (scene_id, seed, played_at),
    )
    conn.commit()


def last_played(conn: Connection) -> dict[str, str]:
    """Je Szene der jüngste Spielzeitpunkt."""
    rows = conn.execute(
        "SELECT scene_id, MAX(played_at) AS played_at FROM game_scene_runs GROUP BY scene_id"
    ).fetchall()
    return {row["scene_id"]: row["played_at"] for row in rows}
