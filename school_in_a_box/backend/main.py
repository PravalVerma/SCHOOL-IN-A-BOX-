# backend/main.py

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from services.ingestion import ingest_text
from agents.explainer import explain_raw_text, explain_with_retrieval
from agents.quiz_generator import generate_mcqs_with_retrieval, MCQ
from services.quizzes import save_quiz, save_response, get_quiz_by_id
from services.progress import compute_progress, get_coaching_for_user
from db.models import init_indexes


app = FastAPI(title="School in a Box API")


# ---------- Pydantic models ----------

class IngestTextRequest(BaseModel):
    text: str
    source_id: str


class ExplainRawRequest(BaseModel):
    text: str
    level: str = "simple"


class ExplainRagRequest(BaseModel):
    question: str
    level: str = "simple"
    k: int = 5


class GenerateQuizRequest(BaseModel):
    user_id: str
    topic_or_question: str
    source_id: str
    num_questions: int = 5
    difficulty: str = "medium"
    k: int = 5


class MCQResponse(BaseModel):
    question: str
    options: List[str]
    correct_index: int
    explanation: Optional[str] = None
    difficulty: str


class SaveResponseRequest(BaseModel):
    user_id: str
    quiz_id: str
    question_index: int
    chosen_index: int
    is_correct: bool


class CoachingRequest(BaseModel):
    user_id: str


# ---------- Startup ----------

@app.on_event("startup")
def on_startup():
    # Ensure Mongo indexes exist
    init_indexes()


# ---------- Routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest/text")
def ingest_text_endpoint(req: IngestTextRequest):
    chunks = ingest_text(req.text, source_id=req.source_id)
    return {"num_chunks": len(chunks)}


@app.post("/explain/raw")
def explain_raw_endpoint(req: ExplainRawRequest):
    explanation = explain_raw_text(req.text, level=req.level)
    return {"explanation": explanation}


@app.post("/explain/rag")
def explain_rag_endpoint(req: ExplainRagRequest):
    explanation = explain_with_retrieval(
        question=req.question,
        level=req.level,
        k=req.k,
    )
    return {"explanation": explanation}


@app.post("/quiz/generate", response_model=dict)
def generate_quiz_endpoint(req: GenerateQuizRequest):
    mcqs: List[MCQ] = generate_mcqs_with_retrieval(
        topic_or_question=req.topic_or_question,
        num_questions=req.num_questions,
        difficulty=req.difficulty,
        k=req.k,
    )
    if not mcqs:
        return {"quiz_id": None, "mcqs": []}

    quiz_id = save_quiz(
        user_id=req.user_id,
        topic=req.topic_or_question,
        source_id=req.source_id,
        mcqs=mcqs,
    )

    mcq_payload = [
        MCQResponse(
            question=m.question,
            options=m.options,
            correct_index=m.correct_index,
            explanation=m.explanation,
            difficulty=m.difficulty,
        )
        for m in mcqs
    ]

    return {
        "quiz_id": quiz_id,
        "mcqs": mcq_payload,
    }


@app.post("/quiz/response")
def save_response_endpoint(req: SaveResponseRequest):
    response_id = save_response(
        user_id=req.user_id,
        quiz_id=req.quiz_id,
        question_index=req.question_index,
        chosen_index=req.chosen_index,
        is_correct=req.is_correct,
    )
    return {"response_id": response_id}


@app.get("/quiz/{quiz_id}")
def get_quiz_endpoint(quiz_id: str):
    quiz_doc = get_quiz_by_id(quiz_id)
    if not quiz_doc:
        return {"quiz": None}
    # _id is ObjectId, we already set 'id' in get_quiz_by_id
    quiz_doc.pop("_id", None)
    return {"quiz": quiz_doc}


@app.post("/coach/advice")
def coaching_endpoint(req: CoachingRequest):
    advice = get_coaching_for_user(req.user_id)
    stats = compute_progress(req.user_id)
    return {"advice": advice, "progress": stats}
