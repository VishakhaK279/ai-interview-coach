"""Application settings loaded from config.yaml with environment overrides."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    agent_mode: Literal["groq", "local"]
    api_key_env: str
    model: str
    api_base_url: str
    request_timeout_seconds: int
    rag_enabled: bool = True
    rag_role: str = "data_engineering"
    rag_collection: str = "data_engineering_rubrics"
    rag_persist_directory: Path = Path(".chroma")
    rag_top_k: int = 4
    rag_chunk_size_chars: int = 1200
    rag_chunk_overlap_chars: int = 150
    rag_ollama_base_url: str = "http://localhost:11434"
    rag_embedding_model: str = "nomic-embed-text"


def load_settings(env_file: Path | None = None) -> Settings:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=env_file or project_root / ".env", override=False)

    config_path = project_root / "config.yaml"
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    agents = config.get("agents", {})
    rag = config.get("rag", {})
    mode = os.getenv("INTERVIEW_AGENT_MODE", agents.get("mode", "groq"))
    if mode not in {"groq", "local"}:
        raise ValueError("INTERVIEW_AGENT_MODE must be 'groq' or 'local'.")

    timeout = int(agents.get("request_timeout_seconds", 30))
    if timeout <= 0:
        raise ValueError("agents.request_timeout_seconds must be greater than zero.")

    chunk_size = int(rag.get("chunk_size_chars", 1200))
    chunk_overlap = int(rag.get("chunk_overlap_chars", 150))
    top_k = int(rag.get("top_k", 4))
    rag_enabled = _parse_bool(
        os.getenv("RAG_ENABLED", str(rag.get("enabled", True))), "RAG_ENABLED"
    )
    if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError(
            "RAG chunk size must be positive and overlap must be smaller than size."
        )
    if top_k <= 0:
        raise ValueError("rag.top_k must be greater than zero.")
    persist_directory = Path(
        os.getenv("RAG_PERSIST_DIRECTORY", str(rag.get("persist_directory", ".chroma")))
    )
    if not persist_directory.is_absolute():
        persist_directory = project_root / persist_directory

    return Settings(
        agent_mode=mode,
        api_key_env=agents.get("api_key_env", "GROQ_API_KEY"),
        model=os.getenv("GROQ_MODEL", agents.get("model", "openai/gpt-oss-120b")),
        api_base_url=os.getenv(
            "GROQ_API_BASE_URL",
            agents.get("api_base_url", "https://api.groq.com/openai/v1"),
        ).rstrip("/"),
        request_timeout_seconds=timeout,
        rag_enabled=rag_enabled,
        rag_role=str(rag.get("role", "data_engineering")),
        rag_collection=str(rag.get("collection", "data_engineering_rubrics")),
        rag_persist_directory=persist_directory,
        rag_top_k=top_k,
        rag_chunk_size_chars=chunk_size,
        rag_chunk_overlap_chars=chunk_overlap,
        rag_ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL", rag.get("ollama_base_url", "http://localhost:11434")
        ).rstrip("/"),
        rag_embedding_model=os.getenv(
            "OLLAMA_EMBEDDING_MODEL", rag.get("embedding_model", "nomic-embed-text")
        ),
    )


def _parse_bool(value: str, setting_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes"}:
        return True
    if normalized in {"0", "false", "no"}:
        return False
    raise ValueError(f"{setting_name} must be a boolean value.")
