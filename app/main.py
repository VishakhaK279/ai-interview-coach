"""FastAPI application entrypoint."""

from fastapi import FastAPI

from app.models.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.pipelines.interview_pipeline import InterviewPipeline

app = FastAPI(
    title="AI Interview Coach",
    description="Generate interview questions and get baseline answer feedback.",
    version="0.1.0",
)
pipeline = InterviewPipeline()


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the API is available."""
    return {"status": "ok"}


@app.post("/interview/questions", response_model=QuestionGenerationResponse)
def generate_questions(
    request: QuestionGenerationRequest,
) -> QuestionGenerationResponse:
    """Generate questions based on a job description."""
    return pipeline.generate_questions(request)


@app.post("/interview/evaluate", response_model=AnswerEvaluationResponse)
def evaluate_answer(
    request: AnswerEvaluationRequest,
) -> AnswerEvaluationResponse:
    """Evaluate an answer against the supplied role skills."""
    return pipeline.evaluate_answer(request)
