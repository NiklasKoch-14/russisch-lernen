from sqlite3 import Connection

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import (
    AnalyzeSessionResponse,
    LearningPlanResponse,
    PlacementAnswerRequest,
    PlacementAnswerResponse,
    PlacementStartResponse,
    PracticeTurnRequest,
    PracticeTurnResponse,
    ProfileResponse,
    VocabAnswerRequest,
    VocabAnswerResponse,
    VocabCardResponse,
)
from app.config import settings
from app.dependencies import get_db, get_ollama
from app.ollama_client import OllamaClient
from app.repositories import vocab_repo
from app.repositories.learning_plan_repo import get_latest_plan
from app.repositories.profile_repo import get_or_create_profile
from app.srs import vocab_service
from app.tutor import analysis_service, dialog_service, placement_service

router = APIRouter(prefix="/api")


@router.get("/profile", response_model=ProfileResponse)
def read_profile(conn: Connection = Depends(get_db)) -> ProfileResponse:
    profile = get_or_create_profile(conn, default_language=settings.default_language)
    return ProfileResponse(language=profile.language, cefr_level=profile.cefr_level)


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
