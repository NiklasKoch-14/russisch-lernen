import datetime as dt
import json
from dataclasses import dataclass
from sqlite3 import Connection


@dataclass
class LearningPlan:
    id: int
    language: str
    topics: list[str]
    created_at: str


def create_plan(conn: Connection, *, language: str, topics: list[str]) -> LearningPlan:
    created_at = dt.datetime.utcnow().isoformat()
    cursor = conn.execute(
        "INSERT INTO learning_plans (language, topics_json, created_at) VALUES (?, ?, ?)",
        (language, json.dumps(topics), created_at),
    )
    conn.commit()
    return LearningPlan(id=cursor.lastrowid, language=language, topics=topics, created_at=created_at)


def get_latest_plan(conn: Connection, *, language: str) -> LearningPlan | None:
    row = conn.execute(
        """SELECT id, language, topics_json, created_at FROM learning_plans
           WHERE language = ? ORDER BY id DESC LIMIT 1""",
        (language,),
    ).fetchone()
    if row is None:
        return None
    return LearningPlan(
        id=row["id"],
        language=row["language"],
        topics=json.loads(row["topics_json"]),
        created_at=row["created_at"],
    )
