from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnswerEvaluationRequest, QuestionGenerationRequest
from app.pipelines.interview_pipeline import InterviewPipeline

client = TestClient(app)


def test_pipeline_generates_and_evaluates_against_role_skills() -> None:
    pipeline = InterviewPipeline()
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
    assert result.score == 50
    assert "Docker" in result.feedback


def test_api_health_and_question_endpoint() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    response = client.post(
        "/interview/questions",
        json={"job_description": "Python developer", "question_count": 1},
    )

    assert response.status_code == 200
    assert response.json()["skills"] == ["Python"]
    assert len(response.json()["questions"]) == 1
