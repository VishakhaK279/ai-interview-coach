"""FastAPI application entrypoint."""

import logging
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Header, HTTPException, Request, Response

from app.guardrails import NOT_SCORED_MESSAGE, log_evaluation
from app.logging_config import configure_logging
from app.llm.groq_client import (
    GroqConfigurationError,
    GroqProviderError,
    GroqResponseError,
)
from app.rag.retriever import RagError
from app.models.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    TranscriptionResponse,
)
from app.pipelines.interview_pipeline import InterviewPipeline

PROJECT_ROOT = Path(__file__).resolve().parents[1]
configure_logging(PROJECT_ROOT / "logs" / "app.log")

app = FastAPI(
    title="AI Interview Coach",
    description="Generate interview questions and get feedback on candidate answers.",
    version="0.1.0",
)
pipeline = InterviewPipeline()
logger = logging.getLogger(__name__)
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@app.get("/health")
def health() -> dict[str, str]:
    """Report whether the API is available."""
    return {"status": "ok"}


@app.post("/interview/questions", response_model=QuestionGenerationResponse)
def generate_questions(
    request: QuestionGenerationRequest,
) -> QuestionGenerationResponse:
    """Generate questions based on a job description."""
    try:
        return pipeline.generate_questions(request)
    except GroqConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GroqProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except GroqResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RagError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/interview/evaluate", response_model=AnswerEvaluationResponse)
def evaluate_answer(
    request: AnswerEvaluationRequest,
    response: Response,
) -> AnswerEvaluationResponse:
    """Evaluate an answer against the supplied role skills."""
    request_id = uuid4().hex
    try:
        result = pipeline.evaluate_answer(request, request_id=request_id)
    except (
        GroqConfigurationError,
        GroqProviderError,
        GroqResponseError,
        RagError,
    ) as exc:
        logger.warning(
            "Evaluation not scored; request_id=%s reason=%s",
            request_id,
            type(exc).__name__,
        )
        result = AnswerEvaluationResponse(
            score=None,
            assessed_skills=[],
            matched_skills=[],
            missing_skills=[],
            feedback=NOT_SCORED_MESSAGE,
            content_safe=True,
            confidence="low",
            answer_relevant=False,
            request_id=request_id,
        )

    response.headers["X-Request-ID"] = request_id
    sources = [source.model_dump() for source in result.sources]
    if not result.content_safe:
        outcome = "blocked_unsafe_content"
        reason = "content_safety"
    elif result.score is None:
        outcome = "not_scored"
        reason = "no_relevant_skills_or_evaluation_failure"
    else:
        outcome = "scored"
        reason = None
    log_evaluation(
        request_id=request_id,
        outcome=outcome,
        score=result.score,
        assessed_skills=result.assessed_skills,
        sources=sources,
        job_description=request.job_description,
        reason=reason,
    )
    if result.score is None:
        result = result.model_copy(
            update={
                "feedback": NOT_SCORED_MESSAGE,
                "confidence": "low",
                "answer_relevant": False,
            }
        )
    return result


@app.post("/interview/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    request: Request,
    filename: str = Header(default="answer.wav", alias="X-Audio-Filename"),
) -> TranscriptionResponse:
    """Transcribe a raw audio request body; audio is not retained or logged."""
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Audio recording must be 25 MB or smaller.",
            )
    if not audio:
        raise HTTPException(status_code=422, detail="Audio recording is empty.")

    try:
        text = pipeline.transcribe_audio(
            bytes(audio),
            filename,
            request.headers.get("content-type", "application/octet-stream"),
        )
    except GroqConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (GroqProviderError, GroqResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return TranscriptionResponse(text=text)
