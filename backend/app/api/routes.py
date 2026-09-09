import datetime as dt
from pathlib import Path
from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.api.schemas import (
    AnalyzeSessionResponse,
    AnswerRequest,
    AnswerResponse,
    ExplainRequest,
    ExplainResponse,
    LearningPlanResponse,
    PlacementAnswerRequest,
    PlacementAnswerResponse,
    PlacementStartResponse,
    PracticeTurnRequest,
    PracticeTurnResponse,
    ProfilePatchRequest,
    ProfileResponse,
    ReviewAnswerRequest,
    ReviewExerciseRequest,
    ScreeningAnswerRequest,
    VocabAnswerRequest,
    VocabAnswerResponse,
    VocabCardResponse,
)
from app.audio.cache import AudioCache, audio_key, strip_stress
from app.config import settings
from app.content.models import Course
from app.course import review as review_module
from app.course import service as course_service
from app.course.review_index import ReviewIndex
from app.dependencies import (
    get_audio_cache,
    get_course,
    get_db,
    get_ollama,
    get_review_index,
    get_tts,
    get_village,
)
from app.game import art as game_art
from app.game import service as game_service
from app.game.models import Village
from app.ollama_client import OllamaClient
from app.tts_client import TtsClient, TtsUnavailable
from app.repositories import vocab_repo
from app.repositories.learning_plan_repo import get_latest_plan
from app.repositories.profile_repo import get_or_create_profile, update_profile
from app.screening import service as screening_service
from app.srs import vocab_service
from app.tutor import analysis_service, dialog_service, placement_service

router = APIRouter(prefix="/api")


@router.get("/profile", response_model=ProfileResponse)
def read_profile(conn: Connection = Depends(get_db)) -> ProfileResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    return ProfileResponse(
        language=profile.language,
        cefr_level=profile.cefr_level,
        show_transliteration=profile.show_transliteration,
        placement_unit=profile.placement_unit,
        audio_autoplay=profile.audio_autoplay,
    )


@router.post("/dialog/practice", response_model=PracticeTurnResponse)
def practice_turn(
    body: PracticeTurnRequest,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PracticeTurnResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    reply = dialog_service.send_practice_turn(conn, ollama=ollama, profile=profile, user_message=body.message)
    return PracticeTurnResponse(reply=reply)


@router.post("/dialog/placement/start", response_model=PlacementStartResponse)
def placement_start(
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PlacementStartResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    session_id, question = placement_service.start_placement(conn, ollama=ollama, language=profile.language)
    return PlacementStartResponse(session_id=session_id, question=question)


@router.post("/dialog/placement/answer", response_model=PlacementAnswerResponse)
def placement_answer(
    body: PlacementAnswerRequest,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> PlacementAnswerResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    finished, result = placement_service.continue_placement(
        conn, ollama=ollama, session_id=body.session_id, language=profile.language, user_answer=body.answer
    )
    if finished:
        return PlacementAnswerResponse(finished=True, level=result)
    return PlacementAnswerResponse(finished=False, question=result)


@router.get("/learning-plan", response_model=LearningPlanResponse)
def read_learning_plan(conn: Connection = Depends(get_db)) -> LearningPlanResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    plan = get_latest_plan(conn, language=profile.language)
    if plan is None:
        raise HTTPException(status_code=404, detail="No learning plan yet")
    return LearningPlanResponse(topics=plan.topics)


@router.post("/session/{session_id}/analyze", response_model=AnalyzeSessionResponse)
def analyze_session_endpoint(
    session_id: int,
    conn: Connection = Depends(get_db),
    ollama: OllamaClient = Depends(get_ollama),
) -> AnalyzeSessionResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    analysis = analysis_service.analyze_session(conn, ollama=ollama, profile=profile, session_id=session_id)
    return AnalyzeSessionResponse(
        updated_level=analysis.get("updated_level"),
        notable_errors=analysis.get("notable_errors", []),
        vocab_suggestions=analysis.get("vocab_suggestions", []),
        next_topics=analysis.get("next_topics", []),
    )


@router.get("/vocab/due", response_model=list[VocabCardResponse])
def read_due_cards(conn: Connection = Depends(get_db)) -> list[VocabCardResponse]:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    cards = vocab_repo.get_due_cards(conn, language=profile.language)
    return [
        VocabCardResponse(
            id=c.id, term=c.term, translation=c.translation,
            example_sentence=c.example_sentence, due_date=c.due_date,
        )
        for c in cards
    ]


@router.post("/vocab/answer", response_model=VocabAnswerResponse)
def answer_vocab_card(
    body: VocabAnswerRequest,
    conn: Connection = Depends(get_db),
) -> VocabAnswerResponse:
    card = vocab_repo.get_card_by_id(conn, card_id=body.card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    correct = vocab_service.submit_answer(conn, card=card, user_answer=body.answer)
    return VocabAnswerResponse(correct=correct)


@router.get("/course")
def read_course(conn: Connection = Depends(get_db), course: Course = Depends(get_course)) -> dict:
    return course_service.course_overview(course, conn)


@router.get("/units/{unit_id}")
def read_unit(
    unit_id: int, conn: Connection = Depends(get_db), course: Course = Depends(get_course)
) -> dict:
    if unit_id not in course.units:
        raise HTTPException(status_code=404, detail=f"Einheit {unit_id} gibt es nicht")
    return course_service.unit_payload(course, conn, unit_id)


@router.post("/units/{unit_id}/answer", response_model=AnswerResponse)
def answer_unit(
    unit_id: int,
    payload: AnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> AnswerResponse:
    if unit_id not in course.units:
        raise HTTPException(status_code=404, detail=f"Einheit {unit_id} gibt es nicht")
    try:
        outcome = course_service.submit_answer(
            conn,
            course,
            unit_id=unit_id,
            exercise_id=payload.exercise_id,
            submission=payload.submission,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AnswerResponse(**vars(outcome))


@router.post("/screening/start")
def screening_start(course: Course = Depends(get_course)) -> dict:
    return screening_service.next_step(course, [])


@router.post("/screening/answer")
def screening_answer(
    payload: ScreeningAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> dict:
    step = screening_service.next_step(course, payload.answers)
    if step["finished"]:
        screening_service.finish_screening(conn, course, payload.answers)
    return step


@router.get("/review/due")
def review_due(
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    index: ReviewIndex = Depends(get_review_index),
) -> dict:
    return review_module.build_review_round(
        conn, course, index, today=dt.date.today().isoformat()
    )


@router.post("/review/answer")
def review_answer(
    payload: ReviewAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    index: ReviewIndex = Depends(get_review_index),
) -> dict:
    return review_module.grade_review_round(
        conn,
        course,
        index,
        today=dt.date.today().isoformat(),
        submission={"pairs": payload.pairs},
    )


@router.post("/review/exercise", response_model=AnswerResponse)
def review_exercise(
    payload: ReviewExerciseRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
) -> AnswerResponse:
    """Eine Kursaufgabe in der Wiederholung — ohne Wirkung auf den Einheiten-Fortschritt."""
    try:
        outcome = course_service.submit_review_exercise(
            conn,
            course,
            unit_id=payload.unit_id,
            exercise_id=payload.exercise_id,
            submission=payload.submission,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AnswerResponse(**vars(outcome))


@router.patch("/profile", response_model=ProfileResponse)
def patch_profile(
    payload: ProfilePatchRequest, conn: Connection = Depends(get_db)
) -> ProfileResponse:
    profile = update_profile(
        conn,
        show_transliteration=payload.show_transliteration,
        placement_unit=payload.placement_unit,
        audio_autoplay=payload.audio_autoplay,
    )
    return ProfileResponse(
        language=profile.language,
        cefr_level=profile.cefr_level,
        show_transliteration=profile.show_transliteration,
        placement_unit=profile.placement_unit,
        audio_autoplay=profile.audio_autoplay,
    )


@router.post("/explain", response_model=ExplainResponse)
def explain(
    payload: ExplainRequest,
    course: Course = Depends(get_course),
    ollama: OllamaClient = Depends(get_ollama),
) -> ExplainResponse:
    unit = course.units.get(payload.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Einheit {payload.unit_id} gibt es nicht")
    rule = unit.grammar_focus.explanation_de
    prompt = (
        "Du bist ein geduldiger Russischlehrer und antwortest auf Deutsch. "
        f"Die Regel dieser Lektion lautet: {rule} "
        f"Der Lernende hat geantwortet: {payload.chosen_text!r}. "
        "Erklaere in hoechstens zwei Saetzen, warum das nicht passt. "
        "Erfinde keine neuen russischen Woerter."
    )
    try:
        text = ollama.chat([{"role": "user", "content": prompt}]).strip()
    except Exception:
        return ExplainResponse(explanation_de=rule, source="rule")
    return ExplainResponse(explanation_de=text or rule, source="llm" if text else "rule")


AUDIO_MAX_CHARS = 300
AUDIO_CACHE_HEADER = "public, max-age=31536000, immutable"


@router.get("/audio/health")
def audio_health(tts: TtsClient = Depends(get_tts)) -> dict:
    """Sagt dem Frontend, ob es Stufe 1 (Server) benutzen kann."""
    return {"available": tts.healthy()}


@router.get("/audio")
def audio(
    text: str = Query(...),
    tts: TtsClient = Depends(get_tts),
    cache: AudioCache = Depends(get_audio_cache),
) -> Response:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Text ist leer")
    if len(cleaned) > AUDIO_MAX_CHARS:
        raise HTTPException(
            status_code=400, detail=f"Text länger als {AUDIO_MAX_CHARS} Zeichen"
        )

    # Gemessen: derselbe Satz mit U+0301 ergibt bei Piper eine andere, laengere
    # Ausgabe. Entfernen macht ausserdem den Schluessel unabhaengig davon, ob der
    # Client die Zeichen mitschickt.
    cleaned = strip_stress(cleaned)

    key = audio_key(
        cleaned,
        voice=settings.piper_voice,
        length_scale=settings.piper_length_scale,
    )
    data = cache.get(key)
    if data is None:
        try:
            data = tts.synthesize(cleaned)
        except TtsUnavailable as exc:
            raise HTTPException(
                status_code=503, detail="Sprachdienst nicht erreichbar"
            ) from exc
        cache.put(key, data)

    return Response(
        content=data,
        media_type="audio/wav",
        headers={"Cache-Control": AUDIO_CACHE_HEADER},
    )


class SceneStartRequest(BaseModel):
    npc_id: str | None = None


class TurnAnswerRequest(BaseModel):
    seed: str
    submission: dict


@router.get("/game/village")
def read_village(village: Village = Depends(get_village)) -> dict:
    return game_service.village_payload(village)


@router.get("/game/places/{place_id}")
def read_place(
    place_id: str,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if place_id not in village.places:
        raise HTTPException(status_code=404, detail=f"Ort {place_id} gibt es nicht")
    return game_service.place_payload(village, course, conn, place_id)


@router.post("/game/places/{place_id}/scene")
def start_scene(
    place_id: str,
    payload: SceneStartRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if place_id not in village.places:
        raise HTTPException(status_code=404, detail=f"Ort {place_id} gibt es nicht")
    try:
        return game_service.start_scene(
            village, course, conn,
            place_id=place_id, npc_id=payload.npc_id,
            now=dt.datetime.now().isoformat(timespec="seconds"),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.get("/game/scenes/{scene_id}/turns/{index}")
def read_turn(
    scene_id: str,
    index: int,
    seed: str,
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if scene_id not in village.scenes:
        raise HTTPException(status_code=404, detail=f"Szene {scene_id} gibt es nicht")
    try:
        return game_service.turn_payload(
            course, village, scene_id=scene_id, seed=seed, index=index
        )
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=f"Zug {index} gibt es nicht") from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=exc.args[0]) from exc


@router.post("/game/scenes/{scene_id}/turns/{index}")
def answer_turn(
    scene_id: str,
    index: int,
    payload: TurnAnswerRequest,
    conn: Connection = Depends(get_db),
    course: Course = Depends(get_course),
    village: Village = Depends(get_village),
) -> dict:
    if scene_id not in village.scenes:
        raise HTTPException(status_code=404, detail=f"Szene {scene_id} gibt es nicht")
    now = dt.datetime.now()
    try:
        return game_service.answer_turn(
            conn, course, village,
            scene_id=scene_id, seed=payload.seed, index=index,
            submission=payload.submission,
            today=now.date().isoformat(), now=now.isoformat(timespec="seconds"),
        )
    except IndexError as exc:
        raise HTTPException(status_code=404, detail=f"Zug {index} gibt es nicht") from exc


@router.get("/game/art/{art_id}")
def read_art(art_id: str) -> FileResponse:
    path = game_art.art_path(Path(settings.game_dir) / "art", art_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Bild {art_id} gibt es nicht")
    return FileResponse(path, media_type=game_art.MEDIA_TYPES[path.suffix])
