# services/quizzes.py
"""
Quiz service layer.

Responsibilities:
- Save generated quizzes (MCQs) to MongoDB.
- Fetch quizzes for a user / by id.
- Record user responses to quiz questions.

This module does NOT generate questions itself; that is handled by:
    agents.quiz_generator.generate_mcqs_from_text / generate_mcqs_with_retrieval
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from datetime import datetime

from bson import ObjectId

from ..db.models import quizzes_col, responses_col
from ..agents.quiz_generator import MCQ


# ---------- Helpers ----------

def _mcq_to_dict(mcq: MCQ) -> Dict[str, Any]:
    return {
        "question": mcq.question,
        "options": mcq.options,
        "correct_index": mcq.correct_index,
        "explanation": mcq.explanation,
        "difficulty": mcq.difficulty,
    }


def _dict_to_mcq(d: Dict[str, Any]) -> MCQ:
    return MCQ(
        question=d.get("question", ""),
        options=d.get("options", []),
        correct_index=d.get("correct_index", 0),
        explanation=d.get("explanation"),
        difficulty=d.get("difficulty", "medium"),
    )


# ---------- Quiz CRUD ----------

def save_quiz(
    user_id: str,
    topic: str,
    source_id: str,
    mcqs: List[MCQ],
) -> str:
    """
    Save a quiz document with embedded MCQs.

    Returns:
        quiz_id (as string)
    """
    if not mcqs:
        raise ValueError("Cannot save quiz with empty MCQ list.")

    doc = {
        "user_id": user_id,
        "topic": topic,
        "source_id": source_id,
        "created_at": datetime.utcnow(),
        "mcqs": [_mcq_to_dict(m) for m in mcqs],
    }

    result = quizzes_col().insert_one(doc)
    return str(result.inserted_id)


def get_quiz_by_id(quiz_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a quiz document by its _id (string form).

    Returns:
        Full quiz document as dict, or None if not found.
    """
    try:
        oid = ObjectId(quiz_id)
    except Exception:
        return None

    doc = quizzes_col().find_one({"_id": oid})
    if not doc:
        return None

    # Optionally normalize _id to string for UI
    doc["id"] = str(doc["_id"])
    return doc


def get_quizzes_for_user(
    user_id: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Fetch recent quizzes for a given user.

    Returns:
        List of quiz docs (with 'id' as string).
    """
    cursor = (
        quizzes_col()
        .find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(limit)
    )
    quizzes: List[Dict[str, Any]] = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        quizzes.append(doc)
    return quizzes


# ---------- Responses ----------

def save_response(
    user_id: str,
    quiz_id: str,
    question_index: int,
    chosen_index: int,
    is_correct: bool,
) -> str:
    """
    Record a single answer to a quiz question.

    Returns:
        response_id (string)
    """
    try:
        quiz_oid = ObjectId(quiz_id)
    except Exception:
        raise ValueError("Invalid quiz_id")

    doc = {
        "user_id": user_id,
        "quiz_id": quiz_oid,
        "question_index": question_index,
        "chosen_index": chosen_index,
        "is_correct": is_correct,
        "answered_at": datetime.utcnow(),
    }
    result = responses_col().insert_one(doc)
    return str(result.inserted_id)


def get_responses_for_user(
    user_id: str,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Fetch recent responses for a user.

    Returns:
        List of response docs (with id as string).
    """
    cursor = (
        responses_col()
        .find({"user_id": user_id})
        .sort("answered_at", -1)
        .limit(limit)
    )
    out: List[Dict[str, Any]] = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        out.append(doc)
    return out


def get_responses_for_quiz(quiz_id: str) -> List[Dict[str, Any]]:
    """
    Fetch all responses for a specific quiz.
    """
    try:
        quiz_oid = ObjectId(quiz_id)
    except Exception:
        return []

    cursor = responses_col().find({"quiz_id": quiz_oid}).sort("answered_at", 1)
    out: List[Dict[str, Any]] = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        out.append(doc)
    return out
