"""Build or update the local Data Engineering rubric vector index."""

from pathlib import Path

from app.rag.retriever import (
    OllamaEmbedder,
    chunk_rubric_markdown,
    load_chroma_store,
)
from app.settings import load_settings


def main() -> None:
    settings = load_settings()
    project_root = Path(__file__).resolve().parents[2]
    rubric_directory = project_root / "data" / "rubrics" / settings.rag_role
    rubric_files = sorted(rubric_directory.rglob("*.md"))
    if not rubric_files:
        raise FileNotFoundError(f"No Markdown rubric files found in {rubric_directory}")

    chunks = [
        chunk
        for rubric_file in rubric_files
        for chunk in chunk_rubric_markdown(
            rubric_file,
            settings.rag_role,
            project_root,
            settings.rag_chunk_size_chars,
            settings.rag_chunk_overlap_chars,
        )
    ]
    if not chunks:
        raise ValueError(f"Rubric files in {rubric_directory} produced no chunks.")

    embedder = OllamaEmbedder(
        settings.rag_ollama_base_url,
        settings.rag_embedding_model,
        settings.request_timeout_seconds,
    )
    store = load_chroma_store(settings)
    embeddings: list[list[float]] = []
    batch_size = 32
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset : offset + batch_size]
        embeddings.extend(embedder.embed([chunk.text for chunk in batch]))
    store.replace_role(settings.rag_role, chunks, embeddings)

    print(
        f"Indexed {len(chunks)} rubric passages for {settings.rag_role} "
        f"using {settings.rag_embedding_model} in {settings.rag_persist_directory}."
    )


if __name__ == "__main__":
    main()
