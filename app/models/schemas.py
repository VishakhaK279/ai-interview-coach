"""Pydantic contracts shared by the API, agents, and pipeline."""

from pydantic import BaseModel, Field


class QuestionGenerationRequest(BaseModel):
    job_description: str = Field(min_length=1)
    question_count: int = Field(default=5, ge=1, le=10)


class QuestionGenerationResponse(BaseModel):
    skills: list[str]
    questions: list[str]


class AnswerEvaluationRequest(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    required_skills: list[str] = Field(default_factory=list)


class EvaluationDetails(BaseModel):
    score: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]


class AnswerEvaluationResponse(EvaluationDetails):
    feedback: str
