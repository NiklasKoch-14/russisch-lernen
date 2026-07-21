from pydantic import BaseModel


class ProfileResponse(BaseModel):
    language: str
    cefr_level: str


class PracticeTurnRequest(BaseModel):
    message: str


class PracticeTurnResponse(BaseModel):
    reply: str


class PlacementStartResponse(BaseModel):
    session_id: int
    question: str


class PlacementAnswerRequest(BaseModel):
    session_id: int
    answer: str


class PlacementAnswerResponse(BaseModel):
    finished: bool
    question: str | None = None
    level: str | None = None


class LearningPlanResponse(BaseModel):
    topics: list[str]


class VocabCardResponse(BaseModel):
    id: int
    term: str
    translation: str
    example_sentence: str
    due_date: str


class VocabAnswerRequest(BaseModel):
    card_id: int
    answer: str


class VocabAnswerResponse(BaseModel):
    correct: bool


class AnalyzeSessionResponse(BaseModel):
    updated_level: str | None = None
    notable_errors: list[str] = []
    vocab_suggestions: list[dict] = []
    next_topics: list[str] = []
