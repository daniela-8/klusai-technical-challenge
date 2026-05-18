"""Embedding service — works with any OpenAI-compatible provider + ChromaDB.
When using Google Gemini:
  model: text-embedding-004
  base_url: https://generativelanguage.googleapis.com/v1beta/openai/
Note: Gemini's embedding model returns 768-dimensional vectors vs OpenAI's 1536.
ChromaDB handles arbitrary dimensions, so this works transparently.
"""

from __future__ import annotations
from pathlib import Path
from typing import Any
import chromadb
from openai import AsyncOpenAI
from app.core import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generate embeddings and perform semantic similarity search via ChromaDB."""

    def __init__(self) -> None:
        self._openai: AsyncOpenAI | None = None
        if settings.has_openai_key:
            kwargs: dict[str, Any] = {"api_key": settings.openai_api_key}
            if settings.openai_base_url:
                kwargs["base_url"] = settings.openai_base_url
            self._openai = AsyncOpenAI(**kwargs)
            logger.info(
                "embeddings_initialized",
                provider="gemini" if settings.openai_base_url else "openai",
                model=settings.openai_embedding_model,
            )
        persist_dir = Path(settings.chroma_persist_dir)
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._chroma.get_or_create_collection(
            name="job_embeddings",
            metadata={"hnsw:space": "cosine"},
        )

    @property
    def is_available(self) -> bool:
        return self._openai is not None

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""
        if not self._openai:
            raise RuntimeError("Embedding client not initialized — missing API key")
        response = await self._openai.embeddings.create(
            model=settings.openai_embedding_model,
            input=text[:8000],
        )
        return response.data[0].embedding

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts in a single batch."""
        if not self._openai:
            raise RuntimeError("Embedding client not initialized — missing API key")
        truncated = [t[:8000] for t in texts]
        response = await self._openai.embeddings.create(
            model=settings.openai_embedding_model,
            input=truncated,
        )
        return [item.embedding for item in response.data]

    async def store_job_embedding(
        self,
        job_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a job's embedding in ChromaDB for later similarity search."""
        embedding = await self.embed_text(text)
        safe_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    safe_metadata[k] = v
                elif v is None:
                    safe_metadata[k] = ""
                else:
                    safe_metadata[k] = str(v)
        self._collection.upsert(
            ids=[job_id],
            embeddings=[embedding],
            documents=[text[:5000]],
            metadatas=[safe_metadata] if safe_metadata else None,
        )
        logger.info("embedding_stored", job_id=job_id)

    async def find_similar_jobs(
        self,
        query_text: str,
        n_results: int = 5,
        exclude_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find jobs semantically similar to the query text."""
        query_embedding = await self.embed_text(query_text)
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results + (1 if exclude_id else 0),
        )
        similar: list[dict[str, Any]] = []
        if results and results["ids"]:
            for i, job_id in enumerate(results["ids"][0]):
                if exclude_id and job_id == exclude_id:
                    continue
                similar.append(
                    {
                        "job_id": job_id,
                        "distance": (
                            results["distances"][0][i] if results["distances"] else 0
                        ),
                        "similarity": 1
                        - (results["distances"][0][i] if results["distances"] else 0),
                        "document": (
                            results["documents"][0][i] if results["documents"] else ""
                        ),
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                    }
                )
                if len(similar) >= n_results:
                    break
        return similar

    def get_collection_count(self) -> int:
        """Return the number of embeddings stored."""
        return self._collection.count()
