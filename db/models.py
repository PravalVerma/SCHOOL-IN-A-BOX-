# db/models.py
"""
MongoDB connection and collection helpers for School in a Box.

This module:
- Creates a single global MongoClient (lazy)
- Exposes get_db() and typed collection helpers
- (Optionally) creates basic indexes

Collections we plan to use:

- users        : user profiles / basic info
- content      : ingested study material metadata
- quizzes      : quiz definitions (per user/topic)
- responses    : user answers to quiz questions
- progress     : aggregated or snapshot progress documents

Actual read/write logic will live in services/quizzes.py and services/progress.py.
"""

from __future__ import annotations

from typing import Any
from pymongo import MongoClient, ASCENDING

from ..config import MONGO_URI, MONGO_DB_NAME

_client: MongoClient | None = None
_db: Any | None = None


def get_client() -> MongoClient:
    """
    Lazily create and return a global MongoClient.
    """
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI)
    return _client


def get_db():
    """
    Return the main application database.
    """
    global _db
    if _db is None:
        client = get_client()
        _db = client[MONGO_DB_NAME]
    return _db


# ---------- Collection helpers ----------

def users_col():
    return get_db()["users"]


def content_col():
    """
    Stores ingested content metadata, e.g.:

    {
      _id: ObjectId,
      user_id: "u123",
      source_id: "physics_ch_1_pdf",
      source_type: "pdf" | "text" | "image",
      title: "Physics Chapter 1",
      created_at: datetime,
      extra: {...}
    }
    """
    return get_db()["content"]


def quizzes_col():
    """
    Stores quiz definitions, e.g.:

    {
      _id: ObjectId,
      user_id: "u123",
      topic: "Kinematics",
      source_id: "physics_ch_1_pdf",
      created_at: datetime,
      mcqs: [
        {
          "question": "...",
          "options": ["A", "B", "C", "D"],
          "correct_index": 1,
          "difficulty": "medium",
          "explanation": "..."
        },
        ...
      ]
    }
    """
    return get_db()["quizzes"]


def responses_col():
    """
    Stores user responses to quiz questions, e.g.:

    {
      _id: ObjectId,
      user_id: "u123",
      quiz_id: ObjectId,
      question_index: 0,
      chosen_index: 2,
      is_correct: True,
      answered_at: datetime
    }
    """
    return get_db()["responses"]


def progress_col():
    """
    Stores aggregated progress or snapshots per user/topic, e.g.:

    {
      _id: ObjectId,
      user_id: "u123",
      computed_at: datetime,
      overall_accuracy: 0.72,
      topics: [
        {"name": "Algebra", "accuracy": 0.55},
        {"name": "Kinematics", "accuracy": 0.82}
      ]
    }
    """
    return get_db()["progress"]


# ---------- Optional: basic indexes ----------

def init_indexes() -> None:
    """
    Create basic indexes for faster queries.
    Safe to call multiple times.
    """
    content_col().create_index([("user_id", ASCENDING)])
    content_col().create_index([("source_id", ASCENDING)])

    quizzes_col().create_index([("user_id", ASCENDING)])
    quizzes_col().create_index([("topic", ASCENDING)])

    responses_col().create_index([("user_id", ASCENDING)])
    responses_col().create_index([("quiz_id", ASCENDING)])

    progress_col().create_index([("user_id", ASCENDING)])
