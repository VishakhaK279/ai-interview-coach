from pathlib import Path

import pytest

from app.agents.answer_evaluator import AnswerEvaluator
from app.agents.feedback_writer import FeedbackWriter
from app.models.schemas import (
    AnswerEvaluationRequest,
    EvaluationDetails,
)
from app.pipelines.interview_pipeline import InterviewPipeline
from app.rag.retriever import (
    KnowledgeBaseNotReadyError,
    ChromaRubricStore,
    EmbeddingServiceError,
    OllamaEmbedder,
    RetrievedRubric,
    RubricChunk,
    RubricRetriever,
    chunk_rubric_markdown,
)


class FakeEmbedder:
    def __init__(self) -> None:
        self.queries: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.queries.append(texts)
        return [[1.0, 0.0] for _ in texts]


class FakeStore:
    def __init__(self, results: list[RetrievedRubric] | None = None) -> None:
        self.results = results or []
        self.last_search: tuple[list[float], str, int] | None = None

    def upsert(
        self, chunks: list[RubricChunk], embeddings: list[list[float]]
    ) -> None:
        assert len(chunks) == len(embeddings)

    def replace_role(
        self,
        role: str,
        chunks: list[RubricChunk],
        embeddings: list[list[float]],
    ) -> None:
        assert all(chunk.role == role for chunk in chunks)
        assert len(chunks) == len(embeddings)

    def search(
        self,
        query_embedding: list[float],
        role: str,
        top_k: int,
        source: str | None = None,
    ) -> list[RetrievedRubric]:
        self.last_search = query_embedding, role, top_k
        return [
            result
            for result in self.results
            if source is None or result.source == source
        ]

    def count(self, role: str | None = None, source: str | None = None) -> int:
        if role is not None and source is None:
            assert all(result.role == role for result in self.results)
        return sum(
            1
            for result in self.results
            if (role is None or result.role == role)
            and (source is None or result.source == source)
        )


def test_chunk_rubric_markdown_keeps_section_metadata_and_stable_ids(tmp_path) -> None:
    corpus = tmp_path / "data" / "rubrics"
    corpus.mkdir(parents=True)
    rubric = corpus / "rubrics.md"
    rubric.write_text(
        "# Intro that should not be indexed\n"
        "## ETL and pipeline design\n"
        "Look at sources, transformations, retries, and measured outcomes.\n"
        "## SQL\n"
        "Assess joins, query plans, and performance measurements.\n",
        encoding="utf-8",
    )

    first = chunk_rubric_markdown(rubric, "data_engineering", tmp_path, 500, 50)
    second = chunk_rubric_markdown(rubric, "data_engineering", tmp_path, 500, 50)

    assert [chunk.skill for chunk in first] == ["ETL and pipeline design", "SQL"]
    assert first[0].chunk_id == second[0].chunk_id
    assert "Intro that should not be indexed" not in first[0].text
    assert first[0].source == "data/rubrics/rubrics.md"


def test_project_data_engineering_corpus_produces_multiple_rubric_chunks() -> None:
    project_root = Path(__file__).resolve().parents[1]
    rubric = project_root / "data" / "rubrics" / "data_engineering" / "rubrics.md"

    chunks = chunk_rubric_markdown(rubric, "data_engineering", project_root, 1200, 150)

    assert len(chunks) >= 7
    assert {chunk.skill for chunk in chunks} >= {
        "ETL and pipeline design",
        "SQL and query performance",
        "Cloud data platforms",
    }
    assert all(chunk.role == "data_engineering" for chunk in chunks)


def test_project_scoring_guide_indexes_all_five_score_bands() -> None:
    project_root = Path(__file__).resolve().parents[1]
    scoring_guide = (
        project_root
        / "data"
        / "rubrics"
        / "data_engineering"
        / "scoring_guide.md"
    )

    chunks = chunk_rubric_markdown(
        scoring_guide, "data_engineering", project_root, 1200, 150
    )

    assert len(chunks) == 5
    assert any("0–20: Limited Evidence" in chunk.text for chunk in chunks)
    assert any("21–40: Basic Competence" in chunk.text for chunk in chunks)
    assert any("41–60: Solid Practitioner" in chunk.text for chunk in chunks)
    assert any("61–80: Strong Candidate" in chunk.text for chunk in chunks)
    assert any("81–100: Exceptional Candidate" in chunk.text for chunk in chunks)


def test_chunker_splits_long_content_with_overlap() -> None:
    from app.rag.retriever import _split_text

    chunks = _split_text("one two three four five six seven", 15, 7)

    assert len(chunks) > 1
    assert all(len(chunk) <= 15 for chunk in chunks)
    assert set(chunks[0].split()) & set(chunks[1].split())


def test_retriever_embeds_query_and_filters_to_configured_role() -> None:
    embedder = FakeEmbedder()
    rubric = RetrievedRubric(
        text="Describe source, transformations, load destination and validation.",
        role="data_engineering",
        skill="ETL and pipeline design",
        source="data/rubrics/data_engineering/rubrics.md",
        distance=0.12,
    )
    store = FakeStore([rubric])
    retriever = RubricRetriever(embedder, store, top_k=3)

    results = retriever.retrieve("How did you validate an ETL pipeline?")

    assert embedder.queries == [["How did you validate an ETL pipeline?"]]
    assert store.last_search == ([1.0, 0.0], "data_engineering", 3)
    assert results == [rubric]


def test_retriever_can_return_all_chunks_from_a_specific_source() -> None:
    scoring_source = "data/rubrics/data_engineering/scoring_guide.md"
    results = [
        RetrievedRubric(
            text=f"Score band {index}",
            role="data_engineering",
            skill=f"Band {index}",
            source=scoring_source,
            distance=0.1,
        )
        for index in range(5)
    ]
    retriever = RubricRetriever(FakeEmbedder(), FakeStore(results), top_k=2)

    retrieved = retriever.retrieve("scoring guide", source=scoring_source)

    assert len(retrieved) == 5
    assert all(result.source == scoring_source for result in retrieved)


def test_retriever_errors_when_index_has_not_been_built() -> None:
    with pytest.raises(KnowledgeBaseNotReadyError, match="build_index"):
        RubricRetriever(FakeEmbedder(), FakeStore()).retrieve("SQL")


def test_ollama_embedder_uses_local_embedding_endpoint(monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr("app.rag.retriever.requests.post", fake_post)
    embedder = OllamaEmbedder("http://localhost:11434/", "nomic-embed-text", 12)

    result = embedder.embed(["ETL pipelines", "SQL performance"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert captured["url"] == "http://localhost:11434/api/embed"
    assert captured["json"] == {
        "model": "nomic-embed-text",
        "input": ["ETL pipelines", "SQL performance"],
    }
    assert captured["timeout"] == 12


def test_ollama_embedder_reports_model_or_server_unavailable(monkeypatch) -> None:
    import requests

    def fail_post(url, **kwargs):
        assert url == "http://localhost:11434/api/embed"
        assert kwargs["json"]["model"] == "nomic-embed-text"
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("app.rag.retriever.requests.post", fail_post)

    with pytest.raises(EmbeddingServiceError, match="nomic-embed-text"):
        OllamaEmbedder("http://localhost:11434", "nomic-embed-text").embed(["SQL"])


def test_chroma_store_upserts_and_filters_by_role(tmp_path) -> None:
    store = ChromaRubricStore(tmp_path / "index", "rubrics", "test-embedder")
    chunks = [
        RubricChunk(
            text="SQL rubric",
            role="data_engineering",
            skill="SQL",
            source="sql.md",
            chunk_id="sql",
        ),
        RubricChunk(
            text="Python rubric",
            role="data_engineering",
            skill="Python",
            source="python.md",
            chunk_id="python",
        ),
        RubricChunk(
            text="Unrelated role rubric",
            role="product_management",
            skill="Planning",
            source="planning.md",
            chunk_id="planning",
        ),
    ]
    store.upsert(chunks, [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]])

    results = store.search([1.0, 0.0], "data_engineering", top_k=1)

    assert store.count() == 3
    assert store.count("data_engineering") == 2
    assert len(results) == 1
    assert results[0].skill == "SQL"
    source_results = store.search(
        [1.0, 0.0],
        "data_engineering",
        top_k=2,
        source="sql.md",
    )
    assert len(source_results) == 1
    assert source_results[0].source == "sql.md"


def test_chroma_store_replace_role_removes_stale_chunks(tmp_path) -> None:
    store = ChromaRubricStore(tmp_path / "index", "rubrics", "test-embedder")
    original = RubricChunk(
        text="Old ETL rubric",
        role="data_engineering",
        skill="ETL",
        source="old.md",
        chunk_id="old",
    )
    updated = RubricChunk(
        text="New ETL rubric",
        role="data_engineering",
        skill="ETL",
        source="new.md",
        chunk_id="new",
    )
    store.upsert([original], [[1.0, 0.0]])

    store.replace_role("data_engineering", [updated], [[0.0, 1.0]])

    assert store.count("data_engineering") == 1
    assert store.search([0.0, 1.0], "data_engineering", 2)[0].source == "new.md"


def test_pipeline_supplies_retrieved_rubric_and_returns_citation() -> None:
    rubric = RetrievedRubric(
        text="Look for source, transformations, destination, and validation.",
        role="data_engineering",
        skill="ETL and pipeline design",
        source="data/rubrics/data_engineering/rubrics.md",
        distance=0.1,
    )
    scoring_guide = RetrievedRubric(
        text="41–60: Solid Practitioner; demonstrates several skills with examples.",
        role="data_engineering",
        skill="41–60: Solid Practitioner",
        source="data/rubrics/data_engineering/scoring_guide.md",
        distance=0.0,
    )

    class FakeRetriever:
        def retrieve(
            self, query: str, source: str | None = None
        ) -> list[RetrievedRubric]:
            if source is not None:
                assert source == "data/rubrics/data_engineering/scoring_guide.md"
                return [scoring_guide]
            assert "Data Engineer" in query
            assert "loaded country data" in query
            return [rubric]

    class FakeEvaluator:
        def evaluate(
            self,
            question: str,
            answer: str,
            required_skills: list[str],
            job_description: str | None = None,
            rubric_context: str | None = None,
        ) -> EvaluationDetails:
            assert question == "Describe an ETL project."
            assert answer == "I used Python and loaded country data into SQLite."
            assert required_skills == ["Python", "ETL", "Cloud Platforms"]
            assert job_description == "Position: Data Engineer"
            assert "source, transformations, destination, and validation" in rubric_context
            assert "41–60: Solid Practitioner" in rubric_context
            return EvaluationDetails(
                score=76,
                assessed_skills=["Python", "ETL"],
                matched_skills=["Python", "ETL"],
                missing_skills=["Cloud Platforms"],
            )

    pipeline = InterviewPipeline(
        answer_evaluator=FakeEvaluator(),
        feedback_writer=FeedbackWriter(),
        rubric_retriever=FakeRetriever(),
    )

    result = pipeline.evaluate_answer(
        AnswerEvaluationRequest(
            question="Describe an ETL project.",
            answer="I used Python and loaded country data into SQLite.",
            required_skills=["Python", "ETL", "Cloud Platforms"],
            job_description="Position: Data Engineer",
        )
    )

    assert result.score == 76
    assert result.assessed_skills == ["Python", "ETL"]
    assert result.sources[0].skill == "ETL and pipeline design"
    assert result.sources[0].source == "data/rubrics/data_engineering/rubrics.md"
    assert result.sources[1].skill == "41–60: Solid Practitioner"
    assert result.sources[1].source.endswith("/scoring_guide.md")


def test_api_explains_that_data_engineering_index_must_be_built(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    import app.main

    monkeypatch.setattr(
        app.main,
        "pipeline",
        InterviewPipeline(
            mode="groq",
            answer_evaluator=AnswerEvaluator(),
            feedback_writer=FeedbackWriter(),
            rubric_retriever=RubricRetriever(FakeEmbedder(), FakeStore()),
        ),
    )
    client = TestClient(app.main.app)

    response = client.post(
        "/interview/evaluate",
        json={
            "question": "Describe an ETL project.",
            "answer": "I extracted and loaded data.",
            "required_skills": ["ETL"],
            "job_description": "Position: Data Engineer",
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] is None
    assert response.json()["feedback"] == (
        "Answer not scored - irrelevant to the question"
    )
