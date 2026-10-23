"""Ollama embeddings and Chroma retrieval for interview rubrics."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import requests

from app.settings import Settings


class RagError(RuntimeError):
    """Base class for explicit RAG configuration and retrieval errors."""


class EmbeddingServiceError(RagError):
    """Raised when the local Ollama embedding service is unavailable."""


class KnowledgeBaseNotReadyError(RagError):
    """Raised when no rubric chunks are available for retrieval."""


@dataclass(frozen=True)
class RubricChunk:
    text: str
    role: str
    skill: str
    source: str
    chunk_id: str


@dataclass(frozen=True)
class RetrievedRubric:
    text: str
    role: str
    skill: str
    source: str
    distance: float


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""


class Retriever(Protocol):
    def retrieve(
        self, query: str, source: str | None = None
    ) -> list[RetrievedRubric]:
        """Retrieve role-scoped passages, optionally restricted to a source."""


class RubricStore(Protocol):
    def upsert(
        self, chunks: list[RubricChunk], embeddings: list[list[float]]
    ) -> None:
        """Insert or update rubric chunks."""

    def replace_role(
        self,
        role: str,
        chunks: list[RubricChunk],
        embeddings: list[list[float]],
    ) -> None:
        """Replace all indexed chunks for a role."""

    def search(
        self,
        query_embedding: list[float],
        role: str,
        top_k: int,
        source: str | None = None,
    ) -> list[RetrievedRubric]:
        """Return the most similar rubric chunks for a role and optional source."""

    def count(self, role: str | None = None, source: str | None = None) -> int:
        """Return the number of indexed chunks."""


class OllamaEmbedder:
    """Create local embeddings using Ollama's /api/embed endpoint."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            embeddings = response.json()["embeddings"]
        except requests.RequestException as exc:
            raise EmbeddingServiceError(
                "Could not reach Ollama for embeddings. Start Ollama and ensure "
                f"the '{self.model}' embedding model is installed."
            ) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise EmbeddingServiceError(
                "Ollama returned an invalid embedding response."
            ) from exc

        if (
            not isinstance(embeddings, list)
            or len(embeddings) != len(texts)
            or any(
                not isinstance(vector, list)
                or not vector
                or any(not isinstance(value, (int, float)) for value in vector)
                for vector in embeddings
            )
        ):
            raise EmbeddingServiceError(
                "Ollama returned an unexpected number or shape of embeddings."
            )
        return embeddings


def load_chroma_store(settings: Settings) -> ChromaRubricStore:
    """Create a persistent Chroma store using configured collection settings."""
    return ChromaRubricStore(
        persist_directory=settings.rag_persist_directory,
        collection_name=settings.rag_collection,
        embedding_model=settings.rag_embedding_model,
    )


class ChromaRubricStore:
    """Persistent Chroma implementation of the rubric store contract."""

    def __init__(
        self,
        persist_directory: Path,
        collection_name: str,
        embedding_model: str,
    ) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RagError(
                "Chroma is not installed. Install project dependencies with "
                "'python -m pip install -r requirements.txt'."
            ) from exc

        persist_directory.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(persist_directory))
        self.collection = client.get_or_create_collection(
            name=collection_name,
            metadata={
                "hnsw:space": "cosine",
                "embedding_model": embedding_model,
            },
        )
        stored_model = (self.collection.metadata or {}).get("embedding_model")
        if stored_model != embedding_model:
            raise RagError(
                f"Vector index uses embedding model {stored_model!r}, but the app "
                f"uses {embedding_model!r}. Rebuild with the configured model or "
                "select the model used to create the index."
            )

    def upsert(
        self, chunks: list[RubricChunk], embeddings: list[list[float]]
    ) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("Each rubric chunk must have exactly one embedding.")
        self.collection.upsert(
            ids=[chunk.chunk_id for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[
                {"role": chunk.role, "skill": chunk.skill, "source": chunk.source}
                for chunk in chunks
            ],
        )

    def replace_role(
        self,
        role: str,
        chunks: list[RubricChunk],
        embeddings: list[list[float]],
    ) -> None:
        if any(chunk.role != role for chunk in chunks):
            raise ValueError("All replacement chunks must match the target role.")
        if len(chunks) != len(embeddings):
            raise ValueError("Each rubric chunk must have exactly one embedding.")
        self.collection.delete(where={"role": role})
        self.upsert(chunks, embeddings)

    def search(
        self,
        query_embedding: list[float],
        role: str,
        top_k: int,
        source: str | None = None,
    ) -> list[RetrievedRubric]:
        if self.count(role, source) == 0:
            return []
        where: dict[str, object] = {"role": role}
        if source is not None:
            where = {"$and": [{"role": role}, {"source": source}]}
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]
        return [
            RetrievedRubric(
                text=document,
                role=metadata["role"],
                skill=metadata["skill"],
                source=metadata["source"],
                distance=distance,
            )
            for document, metadata, distance in zip(
                documents, metadatas, distances, strict=True
            )
        ]

    def count(self, role: str | None = None, source: str | None = None) -> int:
        if role is None and source is None:
            return self.collection.count()
        filters = []
        if role is not None:
            filters.append({"role": role})
        if source is not None:
            filters.append({"source": source})
        where = filters[0] if len(filters) == 1 else {"$and": filters}
        matching = self.collection.get(where=where, include=["metadatas"])
        return len(matching["ids"])


def chunk_rubric_markdown(
    path: Path,
    role: str,
    project_root: Path,
    chunk_size_chars: int,
    overlap_chars: int,
) -> list[RubricChunk]:
    """Split Markdown sections into reproducible character-sized text chunks."""
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive.")
    if overlap_chars < 0 or overlap_chars >= chunk_size_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than chunk size.")

    relative_source = path.resolve().relative_to(project_root.resolve()).as_posix()
    lines = path.read_text(encoding="utf-8").splitlines()
    chunks: list[RubricChunk] = []
    heading = path.stem.replace("_", " ").title()
    section_lines: list[str] = []
    in_section = False

    def flush_section() -> None:
        text = " ".join(line.strip() for line in section_lines if line.strip())
        if not text:
            return
        for index, piece in enumerate(_split_text(text, chunk_size_chars, overlap_chars)):
            chunk_text = f"Skill: {heading}\n{piece}"
            identity = hashlib.sha256(
                f"{relative_source}\0{heading}\0{index}\0{piece}".encode("utf-8")
            ).hexdigest()
            chunks.append(
                RubricChunk(
                    text=chunk_text,
                    role=role,
                    skill=heading,
                    source=relative_source,
                    chunk_id=identity,
                )
            )

    for line in lines:
        if line.startswith("## "):
            if in_section:
                flush_section()
            heading = line[3:].strip()
            section_lines = []
            in_section = True
        elif line.startswith("# "):
            continue
        elif in_section:
            section_lines.append(line)
    if in_section:
        flush_section()
    return chunks


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split at word boundaries while retaining a bounded overlap."""
    words = re.findall(r"\S+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in words:
        added_length = len(word) + (1 if current else 0)
        if current and current_length + added_length > chunk_size:
            chunks.append(" ".join(current))
            overlap_words: list[str] = []
            overlap_length = 0
            for previous_word in reversed(current):
                size = len(previous_word) + (1 if overlap_words else 0)
                if overlap_length + size > overlap:
                    break
                overlap_words.insert(0, previous_word)
                overlap_length += size
            current = overlap_words
            current_length = overlap_length
            added_length = len(word) + (1 if current else 0)
        current.append(word)
        current_length += added_length
    if current:
        chunks.append(" ".join(current))
    return chunks


def build_rubric_retriever(settings: Settings) -> RubricRetriever:
    """Build a Data Engineering rubric retriever from configured components."""
    embedder = OllamaEmbedder(
        settings.rag_ollama_base_url,
        settings.rag_embedding_model,
        settings.request_timeout_seconds,
    )
    return RubricRetriever(
        embedder=embedder,
        store=load_chroma_store(settings),
        role=settings.rag_role,
        top_k=settings.rag_top_k,
    )


class RubricRetriever:
    """Retrieve Data Engineering rubric passages for a query."""

    def __init__(
        self,
        embedder: Embedder,
        store: RubricStore,
        role: str = "data_engineering",
        top_k: int = 4,
    ) -> None:
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        self.embedder = embedder
        self.store = store
        self.role = role
        self.top_k = top_k

    def retrieve(
        self, query: str, source: str | None = None
    ) -> list[RetrievedRubric]:
        matching_count = self.store.count(self.role, source)
        if matching_count == 0:
            raise KnowledgeBaseNotReadyError(
                "The Data Engineering rubric index is empty. Build it with "
                "'python -m app.rag.build_index'."
            )
        query_embedding = self.embedder.embed([query])[0]
        results = self.store.search(
            query_embedding,
            self.role,
            matching_count if source is not None else self.top_k,
            source,
        )
        if not results:
            raise KnowledgeBaseNotReadyError(
                "No Data Engineering rubric passages were found for this query."
            )
        return results
