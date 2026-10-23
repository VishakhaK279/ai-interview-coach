"""Pydantic contracts shared by the API, agents, and pipeline."""

from typing import Literal

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
    job_description: str | None = None


class SkillEvidence(BaseModel):
    skill: str
    level: Literal["none", "mention", "example", "detailed"]


class EvaluationDetails(BaseModel):
    score: int | None = Field(default=None, ge=0, le=100)
    confidence: Literal["high", "medium", "low"] = "medium"
    answer_relevant: bool = True
    assessed_skills: list[str] = Field(default_factory=list)
    skill_evidence: list[SkillEvidence] = Field(default_factory=list)
    matched_skills: list[str]
    missing_skills: list[str]
    content_safe: bool = True


class TranscriptionResponse(BaseModel):
    text: str = Field(min_length=1)


class EvaluationSource(BaseModel):
    skill: str
    source: str


class AnswerEvaluationResponse(EvaluationDetails):
    feedback: str
    sources: list[EvaluationSource] = Field(default_factory=list)
    request_id: str
