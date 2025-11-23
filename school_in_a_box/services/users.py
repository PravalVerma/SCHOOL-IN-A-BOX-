# services/users.py
"""
User service.

Responsibilities:
- Ensure a user document exists.
- List existing users (for switching in the UI).
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from db.models import users_col


def ensure_user(user_id: str) -> None:
    """
    Create or update a user document with this user_id.
    """
    if not user_id.strip():
        return

    users_col().update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {"created_at": datetime.utcnow()},
            "$set": {"last_active_at": datetime.utcnow()},
        },
        upsert=True,
    )


def get_all_user_ids(limit: int = 50) -> List[str]:
    """
    Return a list of user_ids, most recently active first.
    """
    cursor = (
        users_col()
        .find({}, {"user_id": 1, "_id": 0})
        .sort("last_active_at", -1)
        .limit(limit)
    )
    return [doc["user_id"] for doc in cursor if "user_id" in doc]
