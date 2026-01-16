"""
Responsibilities:
- Generate MCQs from given content (text-based).
- Optionally, use retrieved context from the vector store given a topic/question.
- Return a structured list of MCQs, not just plain text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import json

from models.llm_client import LLMClient
from config import LLM_MODEL_QUIZ, DEFAULT_NUM_QUESTIONS
from services.vector_store import store as vector_store



_llm = LLMClient(model_name=LLM_MODEL_QUIZ)


@dataclass
class MCQ:
    question: str
    options: List[str]
    correct_index: int  # 0-based index into options
    explanation: Optional[str] = None
    difficulty: str = "medium"


def _build_quiz_prompt(
    content: str,
    num_questions: int,
    difficulty: str,
) -> str:
    return f"""
ROLE:
You are a Quiz Generator Agent for an educational platform.

OBJECTIVE:
Create high-quality multiple-choice questions that test conceptual understanding.

INPUT MATERIAL:
\"\"\"{content}\"\"\"

REQUIREMENTS:
- Generate exactly {num_questions} MCQs.
- Difficulty level: {difficulty}.
- Each question must test understanding, not memorization.
- Only ONE correct option per question.
- All options must be plausible.

FOR EACH QUESTION, PROVIDE:
- question
- options (list of strings)
- correct_index (0-based)
- difficulty
- short explanation (1–2 lines, grounded in content)

CONSTRAINTS:
- Do NOT introduce concepts not present in the material.
- Do NOT reuse wording from the content verbatim unless necessary.
- Avoid trick questions.

OUTPUT FORMAT:
Return a JSON-style list of objects (no markdown).
""".strip()



def _parse_mcq_json(raw: str, difficulty: str) -> List[MCQ]:
    """
    Parse the model's JSON output into a list of MCQ objects.
    If parsing fails, return an empty list.
    """
    try:
        data = json.loads(raw)
        mcqs: List[MCQ] = []
        if not isinstance(data, list):
            return []

        for item in data:
            q = item.get("question")
            options = item.get("options", [])
            idx = item.get("correct_index", 0)
            expl = item.get("explanation", "")
            diff = item.get("difficulty", difficulty)

            if not q or not isinstance(options, list) or len(options) != 4:
                continue
            if not isinstance(idx, int) or not (0 <= idx < 4):
                idx = 0

            mcqs.append(
                MCQ(
                    question=q,
                    options=options,
                    correct_index=idx,
                    explanation=expl or None,
                    difficulty=diff,
                )
            )
        return mcqs
    except Exception:
        return []


# ---------- Public functions ----------

def generate_mcqs_from_text(
    text: str,
    num_questions: int = DEFAULT_NUM_QUESTIONS,
    difficulty: str = "medium",
) -> List[MCQ]:
    """
    Generate MCQs directly from the provided text (no retrieval).
    """
    prompt = _build_quiz_prompt(text, num_questions, difficulty)
    messages = [
        {"role": "system", "content": "You generate high-quality quizzes for students."},
        {"role": "user", "content": prompt},
    ]
    raw = _llm.chat(messages)
    mcqs = _parse_mcq_json(raw, difficulty=difficulty)

    # If parsing fails, return empty list; caller can decide how to handle.
    return mcqs


def generate_mcqs_with_retrieval(
    topic_or_question: str,
    num_questions: int = DEFAULT_NUM_QUESTIONS,
    difficulty: str = "medium",
    k: int = 5,
) -> List[MCQ]:
    """
    Generate MCQs using stored material related to a topic/question.

    Steps:
    - Retrieve top-k chunks from the vector store based on the topic/question.
    - Use those chunks as the content for quiz generation.
    """
    hits = vector_store.similarity_search(topic_or_question, k=k)
    if not hits:
        # No context; fall back to using the topic/question as raw content.
        return generate_mcqs_from_text(topic_or_question, num_questions, difficulty)

    # Concatenate retrieved chunks into one content string
    chunks = [t for (t, _score) in hits]
    content = "\n\n".join(chunks)

    return generate_mcqs_from_text(content, num_questions, difficulty)
