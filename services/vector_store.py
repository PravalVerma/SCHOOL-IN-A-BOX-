# services/vector_store.py
"""
FAISS vector store wrapper.

Stores embeddings + associated text chunks.
Used by the Content Explainer and Quiz systems to retrieve relevant material.
"""

from typing import List, Dict, Tuple
import faiss
import numpy as np
from pathlib import Path
import pickle

from ..models.embeddings import embed_texts
from ..config import FAISS_INDEX_DIR


class FAISSVectorStore:
    def __init__(self, index_dir: Path = FAISS_INDEX_DIR):
        self.index_dir = index_dir
        self.index_path = index_dir / "index.faiss"
        self.metadata_path = index_dir / "metadata.pkl"

        self.index = None  # FAISS object
        self.metadata: List[Dict] = []  # stores info about each chunk

        self._load_or_init()

    def _load_or_init(self):
        """
        If a FAISS index already exists on disk, load it.
        Otherwise initialize a fresh one.
        """
        self.index_dir.mkdir(parents=True, exist_ok=True)

        if self.index_path.exists() and self.metadata_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
        else:
            self.index = None
            self.metadata = []

    def _save(self):
        """Persist index + metadata to disk."""
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_texts(self, texts: List[str], source_id: str) -> None:
        """
        Embed texts and add them to the FAISS index.

        Parameters:
            texts: list of document chunks
            source_id: identifier (used later for grouping / retrieval)
        """
        embeddings = embed_texts(texts).astype("float32")

        # Create index if first time
        if self.index is None:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dim)

        # Add embeddings
        self.index.add(embeddings)

        # Track metadata
        for t in texts:
            self.metadata.append({
                "text": t,
                "source_id": source_id
            })

        self._save()

    def similarity_search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """
        Return (text, score) tuples sorted by similarity (lower score = more similar).
        """
        if self.index is None or len(self.metadata) == 0:
            return []

        q_emb = embed_texts([query]).astype("float32")
        distances, ids = self.index.search(q_emb, k)

        results = []
        for idx, dist in zip(ids[0], distances[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            results.append((self.metadata[idx]["text"], float(dist)))

        return results


# Singleton instance for project-wide use
store = FAISSVectorStore()