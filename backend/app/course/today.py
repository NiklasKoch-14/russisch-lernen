"""Der Tagesplan der Startseite: auffrischen, eine neue Einheit, anwenden.

Die Reihenfolge ist die einer guten Stunde — erst warm werden mit dem, was man
kann, dann Neues bei frischem Kopf, zum Schluss benutzen. Der Plan wird bei
jedem Aufruf aus den Zeitstempeln abgeleitet; einen Tageszustand speichert
niemand. Was heute erledigt wurde, bleibt dadurch mit Haken stehen, und der
Plan übersteht jeden Neustart.

Dosiert wird bewusst: jede Einheit erzeugt rund zwanzig Wiederholungseinträge,
weil jede Wortform einzeln geplant wird. Wer in der ersten Woche drei
Einheiten am Tag macht, steht drei Wochen später vor einem Berg. Gesperrt wird
trotzdem nichts — der Plan schlägt nur vor. Die Regeln im Einzelnen stehen in
docs/superpowers/specs/2026-09-11-speaker-today-start-page-design.md.
"""

import datetime as dt
import math
from dataclasses import dataclass
from sqlite3 import Connection

from app.config import settings
from app.content.models import Course
from app.course import listening
from app.course import review as review_module
from app.course.review_index import ReviewIndex
from app.game.models import Village
from app.repositories import (
    activity_repo,
    game_repo,
    lexeme_srs_repo,
    listening_repo,
    progress_repo,
    review_repo,
)
from app.repositories.profile_repo import get_or_create_profile

DAILY_REVIEW_CAP = 20
"""So viele Formen frischt der Plan am Tag auf; der Rest wartet still auf morgen."""

BACKLOG_LIMIT = 40
"""Stehen mehr Formen an, kommt keine neue Einheit dazu."""

PAUSE_DAYS = 7
"""Wer länger weg war, frischt am ersten Tag zurück nur auf."""

SECONDS_PER_FORM = 25
LISTENING_MINUTES = 3
SCENE_MINUTES = 4


@dataclass(frozen=True)
class _Practice:
    """Ein Hörgespräch oder eine Dorfszene als Kandidat fürs Anwenden."""

    kind: str
    """listening oder scene — die Reihenfolge der Wörter ist zugleich der Gleichstand."""
    id: str
    unit: int
    last_played: str | None


def _day(timestamp: str) -> str:
    return timestamp[:10]


def _due_forms(conn: Connection, course: Course, today: str) -> int:
    """Fällige Formen, die es im Lexikon noch gibt — wie in der Wiederholung selbst."""
    return sum(
        1
        for state in lexeme_srs_repo.due_states(conn, today=today, limit=None)
        if state.lexeme_id in course.lexemes
        and state.form_key in course.lexemes[state.lexeme_id].forms
    )


def _review_step(due: int, reviewed: int) -> dict | None:
    if due == 0 and reviewed == 0:
        return None
    done = reviewed >= DAILY_REVIEW_CAP or due == 0
    remaining = 0 if done else min(due, DAILY_REVIEW_CAP - reviewed)
    return {
        "kind": "review",
        "done": done,
        "minutes": max(1, math.ceil(remaining * SECONDS_PER_FORM / 60)) if remaining else 0,
        "title_de": "Auffrischen",
        "link": "/wiederholen",
    }


def _unit_step(course: Course, unit_id: int, *, done: bool) -> dict:
    unit = course.units[unit_id]
    return {
        "kind": "unit",
        "done": done,
        "minutes": math.ceil(len(unit.exercises) + 0.5 * len(unit.new_lexemes)),
        "unit_id": unit.id,
        "title_de": unit.title_de,
        "detail_de": unit.scenario_de,
        "link": f"/kurs/{unit.id}",
    }


def _next_unit(course: Course, progress: dict, start: int) -> int | None:
    """Angefangenes zuerst, sonst die erste offene Einheit ab der Einstufung."""
    started = sorted(
        unit_id
        for unit_id, entry in progress.items()
        if entry.status == "in_progress" and unit_id in course.units
    )
    if started:
        return started[0]
    completed = {unit_id for unit_id, entry in progress.items() if entry.status == "completed"}
    return next(
        (
            unit.id
            for unit in course.ordered_units()
            if unit.id >= start and unit.id not in completed
        ),
        None,
    )


def _practice_step(practice: _Practice, course: Course, village: Village, today: str) -> dict:
    known = practice.last_played is not None and _day(practice.last_played) != today
    if practice.kind == "listening":
        dialog = course.dialogs[int(practice.id)]
        return {
            "kind": "listening",
            "minutes": LISTENING_MINUTES,
            "title_de": dialog.title_de,
            "detail_de": None,
            "known": known,
            "link": f"/hoeren?gespraech={dialog.id}",
        }
    scene = village.scenes[practice.id]
    place = village.places.get(scene.place)
    return {
        "kind": "scene",
        "minutes": SCENE_MINUTES,
        "title_de": scene.title_de,
        "detail_de": place.name_de if place else None,
        "known": known,
        "link": f"/dorf/{scene.place}?szene={scene.id}",
    }


def _pick_practice(
    conn: Connection,
    course: Course,
    village: Village,
    *,
    today: str,
    focus: int,
    welcome_back: bool,
) -> dict | None:
    heard = listening_repo.last_played(conn)
    played = game_repo.last_played(conn)
    everything = [
        _Practice("listening", str(dialog.id), dialog.min_unit, heard.get(dialog.id))
        for dialog in course.dialogs.values()
    ] + [
        _Practice("scene", scene.id, scene.hint_unit, played.get(scene.id))
        for scene in village.scenes.values()
    ]

    # Heute schon gehört oder gespielt — auch außerhalb des Plans, und auch
    # eine Szene, deren Einheit noch nicht erreicht ist: das Dorf ist offen.
    today_ones = [p for p in everything if p.last_played and _day(p.last_played) == today]
    if today_ones:
        latest = max(today_ones, key=lambda p: p.last_played or "")
        return {**_practice_step(latest, course, village, today), "done": True}

    reached = listening.reached_unit(conn)
    candidates = [p for p in everything if p.unit <= reached]
    if welcome_back and any(p.last_played for p in candidates):
        # Nach der Pause etwas Bekanntes: man merkt, dass noch alles da ist.
        known = [p for p in candidates if p.last_played]
        chosen = min(known, key=lambda p: (p.last_played or "", p.kind, p.id))
    elif candidates:
        chosen = min(
            candidates,
            key=lambda p: (
                p.last_played is not None,
                abs(p.unit - focus),
                p.last_played or "",
                p.kind,
                p.id,
            ),
        )
    else:
        return None
    return {**_practice_step(chosen, course, village, today), "done": False}


def build_plan(
    conn: Connection, course: Course, village: Village, index: ReviewIndex, *, today: str
) -> dict:
    profile = get_or_create_profile(conn, settings.default_language)
    progress = progress_repo.all_progress(conn)
    active = activity_repo.active_days(conn)

    before = [day for day in active if day < today]
    today_date = dt.date.fromisoformat(today)
    welcome_back = bool(before) and (
        today_date - dt.date.fromisoformat(max(before))
    ).days > PAUSE_DAYS

    due = _due_forms(conn, course, today)
    reviewed = review_repo.count_on(conn, today)

    # Faellig heisst nicht zeigbar: eine einzelne Form ohne Kursaufgabe ergibt
    # keine Zuordnung und wartet auf Gesellschaft. Ob die Wiederholung gerade
    # etwas anbieten kann, entscheidet sie selbst — sonst schickte der Plan zu
    # einem Auffrischen, das „nichts zu wiederholen" sagt.
    presentable = bool(
        due and review_module.build_review_round(conn, course, index, today=today)["items"]
    )

    steps: list[dict] = []
    review = _review_step(due if presentable else 0, reviewed)
    if review:
        steps.append(review)

    finished_today = sorted(
        (entry.completed_at, unit_id)
        for unit_id, entry in progress.items()
        if entry.status == "completed"
        and entry.completed_at
        and _day(entry.completed_at) == today
        and unit_id in course.units
    )
    next_unit = _next_unit(course, progress, profile.placement_unit or 1)
    unit_skipped = None
    if finished_today:
        steps.append(_unit_step(course, finished_today[-1][1], done=True))
    elif next_unit is None:
        unit_skipped = "all_done"
    elif welcome_back:
        unit_skipped = "pause"
    elif due + reviewed > BACKLOG_LIMIT:
        # Die Summe statt der Fälligen allein: sonst tauchte die Einheit mitten
        # am Tag auf, sobald ein paar Formen abgearbeitet sind.
        unit_skipped = "backlog"
    else:
        steps.append(_unit_step(course, next_unit, done=False))

    focus = finished_today[-1][1] if finished_today else listening.reached_unit(conn)
    practice = _pick_practice(
        conn, course, village, today=today, focus=focus, welcome_back=welcome_back
    )
    if practice:
        steps.append(practice)

    upcoming = True
    for step in steps:
        done = step.pop("done")
        if done:
            step["status"] = "done"
        else:
            step["status"] = "next" if upcoming else "later"
            upcoming = False

    monday = (today_date - dt.timedelta(days=today_date.weekday())).isoformat()
    return {
        "greeting": "welcome_back" if welcome_back else "normal",
        "steps": steps,
        "unit_skipped": unit_skipped,
        "next_unit_id": next_unit,
        "finished": bool(steps) and all(step["status"] == "done" for step in steps),
        "week_days": sum(1 for day in active if monday <= day <= today),
        "offer_screening": not active and profile.placement_unit is None and not progress,
    }
