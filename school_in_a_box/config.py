# config.py
"""
Central configuration for School in a Box.

Everything that other modules need (API keys, model names, URIs, paths)
should be defined here, so we don't scatter constants across the codebase.
"""
from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path

# --- Base paths ---

# Root of the project (directory that contains this config.py)
BASE_DIR = Path(__file__).resolve().parent

# Folder for any local indices / cached data if needed
DATA_DIR = BASE_DIR / "data"
FAISS_INDEX_DIR = DATA_DIR / "faiss_index"


# --- Environment variables / secrets ---

# You will export these in your shell or .env:
#   export OPENROUTER_API_KEY="..."
#   export MONGO_URI="mongodb://localhost:27017"
#   export MONGO_DB_NAME="school_in_a_box"
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL: str = os.getenv(
    "OPENROUTER_BASE_URL",
    "https://openrouter.ai/api/v1",
)

MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "School In a Box")


# --- Models & embeddings ---

# Same embedding model you used in your previous Agentic RAG project
EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

# Core LLMs (we can keep them same for now and specialize later if needed)
LLM_MODEL_EXPLAINER: str = "x-ai/grok-4.1-fast"
LLM_MODEL_QUIZ: str = "x-ai/grok-4.1-fast"
LLM_MODEL_COACH: str = "x-ai/grok-4.1-fast"

# --- Vector store selection ---

# For now we’ll default to FAISS (local). Later we can switch to "qdrant"
# and add the qdrant-related config when we wire it.
VECTOR_STORE_TYPE: str = os.getenv("VECTOR_STORE_TYPE", "faiss")  # "faiss" or "qdrant"


# --- Misc app settings ---

# Maximum chunk size for text splitting (will be used in services.ingestion)
CHUNK_SIZE: int = 800
CHUNK_OVERLAP: int = 100

# Default number of quiz questions if user doesn’t specify
DEFAULT_NUM_QUESTIONS: int = 5
