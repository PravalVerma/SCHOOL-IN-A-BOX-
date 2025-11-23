# backend/graphs.py

from __future__ import annotations

from typing import List
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END  # LangGraph

from agents.quiz_generator import MCQ, generate_mcqs_with_retrieval
from services.quizzes import save_quiz


class QuizState(TypedDict, total=False):
    # input fields
    user_id: str
    topic_or_question: str
    source_id: str
    num_questions: int
    difficulty: str
    k: int

    # output fields
    mcqs: List[MCQ]
    quiz_id: str | None


def generate_mcqs_node(state: QuizState) -> QuizState:
    """
    Node 1: use retrieval + LLM to generate MCQs.
    """
    mcqs = generate_mcqs_with_retrieval(
        topic_or_question=state["topic_or_question"],
        num_questions=state.get("num_questions", 5),
        difficulty=state.get("difficulty", "medium"),
        k=state.get("k", 5),
    )
    return {"mcqs": mcqs}


def save_quiz_node(state: QuizState) -> QuizState:
    """
    Node 2: save MCQs into Mongo as a quiz.
    """
    mcqs = state.get("mcqs") or []
    if not mcqs:
        return {"quiz_id": None}

    quiz_id = save_quiz(
        user_id=state["user_id"],
        topic=state["topic_or_question"],
        source_id=state["source_id"],
        mcqs=mcqs,
    )
    return {"quiz_id": quiz_id}


# ---- Build the graph ----

builder = StateGraph(QuizState)
builder.add_node("generate_mcqs", generate_mcqs_node)
builder.add_node("save_quiz", save_quiz_node)

builder.add_edge(START, "generate_mcqs")
builder.add_edge("generate_mcqs", "save_quiz")
builder.add_edge("save_quiz", END)

quiz_graph = builder.compile()
