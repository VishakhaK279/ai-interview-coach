from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnswerEvaluationRequest, QuestionGenerationRequest
from app.pipelines.interview_pipeline import InterviewPipeline

client = TestClient(app)


def test_pipeline_generates_and_evaluates_against_role_skills() -> None:
    pipeline = InterviewPipeline(mode="local")
    question_set = pipeline.generate_questions(
        QuestionGenerationRequest(
            job_description="Looking for Python and Docker experience.",
            question_count=2,
        )
    )
    result = pipeline.evaluate_answer(
        AnswerEvaluationRequest(
            question=question_set.questions[0],
            answer="I built a Python service.",
            required_skills=question_set.skills,
        )
    )

    assert question_set.skills == ["Python", "Docker"]
    assert len(question_set.questions) == 2
    assert result.score == 100
    assert result.assessed_skills == ["Python"]
    assert result.answer_relevant is True
    assert result.request_id
    assert "Docker" not in result.feedback


def test_api_health_and_question_endpoint(monkeypatch) -> None:
    import app.main

    monkeypatch.setattr(app.main, "pipeline", InterviewPipeline(mode="local"))

    assert client.get("/health").json() == {"status": "ok"}
    response = client.post(
        "/interview/questions",
        json={"job_description": "Python developer", "question_count": 1},
    )

    assert response.status_code == 200
    assert response.json()["skills"] == ["Python"]
    assert len(response.json()["questions"]) == 1


def test_api_transcribes_raw_audio_without_logging_or_persisting(monkeypatch) -> None:
    import app.main

    class TranscribingPipeline:
        def transcribe_audio(self, audio, filename, content_type):
            assert audio == b"test audio bytes"
            assert filename == "candidate-answer.webm"
            assert content_type == "audio/webm"
            return "I built a Python data pipeline."

    monkeypatch.setattr(app.main, "pipeline", TranscribingPipeline())
    response = client.post(
        "/interview/transcribe",
        content=b"test audio bytes",
        headers={
            "Content-Type": "audio/webm",
            "X-Audio-Filename": "candidate-answer.webm",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"text": "I built a Python data pipeline."}


def test_api_reports_missing_groq_key(monkeypatch) -> None:
    import app.main

    monkeypatch.setattr(app.main, "pipeline", InterviewPipeline(mode="groq"))
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.post(
        "/interview/questions",
        json={"job_description": "Python developer", "question_count": 1},
    )

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


def test_evaluation_api_returns_request_id_and_logs_metadata_only(
    monkeypatch, caplog
) -> None:
    import logging

    import app.main

    monkeypatch.setattr(app.main, "pipeline", InterviewPipeline(mode="local"))
    caplog.set_level(logging.INFO, logger="app.evaluation.audit")
    job_description = "Python developer"
    private_answer_detail = "PRIVATE candidate answer text"
    answer = f"I used Python to automate this task. {private_answer_detail}"
    response = client.post(
        "/interview/evaluate",
        json={
            "question": "Tell me about a Python project.",
            "answer": answer,
            "required_skills": ["Python", "SQL", "Git"],
            "job_description": job_description,
        },
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["score"] == 100
    assert payload["assessed_skills"] == ["Python"]
    assert payload["request_id"] == response.headers["X-Request-ID"]
    assert payload["content_safe"] is True
    assert payload["confidence"] == "low"
    assert payload["answer_relevant"] is True
    assert private_answer_detail not in caplog.text
    assert job_description not in caplog.text
    assert payload["request_id"] in caplog.text
    assert "job_description_sha256" in caplog.text


def test_evaluation_api_returns_retry_fallback_on_evaluator_failure(monkeypatch) -> None:
    import app.main
    from app.llm.groq_client import GroqResponseError

    class FailingPipeline:
        def evaluate_answer(self, request, request_id=None):
            raise GroqResponseError("Provider response was invalid.")

    monkeypatch.setattr(app.main, "pipeline", FailingPipeline())
    response = client.post(
        "/interview/evaluate",
        json={
            "question": "Tell me about Python.",
            "answer": "I used Python.",
            "required_skills": ["Python"],
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] is None
    assert response.json()["feedback"] == (
        "Answer not scored - irrelevant to the question"
    )
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_evaluation_api_returns_retry_fallback_when_no_skill_is_relevant(
    monkeypatch,
) -> None:
    import app.main

    monkeypatch.setattr(app.main, "pipeline", InterviewPipeline(mode="local"))
    response = client.post(
        "/interview/evaluate",
        json={
            "question": "Tell me about a challenge you overcame.",
            "answer": "I organized a community event.",
            "required_skills": ["Python", "SQL"],
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] is None
    assert response.json()["feedback"] == (
        "Answer not scored - irrelevant to the question"
    )


def test_evaluation_api_does_not_return_a_score_for_unsafe_content(monkeypatch) -> None:
    import app.main
    from app.models.schemas import AnswerEvaluationResponse

    class UnsafePipeline:
        def evaluate_answer(self, request, request_id=None):
            return AnswerEvaluationResponse(
                score=None,
                assessed_skills=[],
                matched_skills=[],
                missing_skills=[],
                content_safe=False,
                feedback="Should be replaced by the safe fallback.",
                request_id=request_id,
            )

    monkeypatch.setattr(app.main, "pipeline", UnsafePipeline())
    response = client.post(
        "/interview/evaluate",
        json={
            "question": "Tell me about Python.",
            "answer": "unsafe text",
            "required_skills": ["Python"],
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] is None
    assert response.json()["content_safe"] is False
    assert response.json()["feedback"] == (
        "Answer not scored - irrelevant to the question"
    )
