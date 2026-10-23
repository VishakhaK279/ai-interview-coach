"""Orchestration for the interview-coaching agents."""

import re
from uuid import uuid4

from app.agents.answer_evaluator import AnswerEvaluator
from app.agents.feedback_writer import FeedbackWriter
from app.agents.question_generator import QuestionGenerator
from app.models.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    EvaluationDetails,
    EvaluationSource,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.llm.groq_client import GroqChatClient
from app.llm.groq_audio_client import GroqAudioTranscriber
from app.rag.retriever import RetrievedRubric, Retriever, build_rubric_retriever
from app.settings import load_settings
from app.utils.jd_parser import extract_skills


class InterviewPipeline:
    """Coordinate independently replaceable agents for API workflows."""

    def __init__(
        self,
        question_generator: QuestionGenerator | None = None,
        answer_evaluator: AnswerEvaluator | None = None,
        feedback_writer: FeedbackWriter | None = None,
        mode: str | None = None,
        rubric_retriever: Retriever | None = None,
    ) -> None:
        settings = load_settings()
        selected_mode = mode or settings.agent_mode
        if selected_mode not in {"groq", "local"}:
            raise ValueError("mode must be 'groq' or 'local'.")
        self.settings = settings
        self.mode = selected_mode
        self.rubric_retriever = rubric_retriever
        llm_client = GroqChatClient(settings) if selected_mode == "groq" else None
        self.question_generator = question_generator or QuestionGenerator(llm_client)
        self.answer_evaluator = answer_evaluator or AnswerEvaluator(llm_client)
        self.feedback_writer = feedback_writer or FeedbackWriter(llm_client)

    def generate_questions(
        self, request: QuestionGenerationRequest
    ) -> QuestionGenerationResponse:
        skills = extract_skills(request.job_description)
        questions = self.question_generator.generate(
            request.job_description,
            request.question_count,
        )
        return QuestionGenerationResponse(skills=skills, questions=questions)

    def evaluate_answer(
        self,
        request: AnswerEvaluationRequest,
        request_id: str | None = None,
    ) -> AnswerEvaluationResponse:
        evaluation_request_id = request_id or uuid4().hex
        retrieved: list[RetrievedRubric] = []
        if (
            self.mode == "groq"
            and self.settings.rag_enabled
            and _is_data_engineering_role(request.job_description)
        ):
            if self.rubric_retriever is None:
                self.rubric_retriever = build_rubric_retriever(self.settings)
            query = "\n".join(
                (
                    request.job_description or "",
                    "Role skills: " + ", ".join(request.required_skills),
                    "Interview question: " + request.question,
                    "Candidate response: " + request.answer,
                )
            )
            retrieved = self.rubric_retriever.retrieve(query)
            scoring_guide_source = (
                f"data/rubrics/{self.settings.rag_role}/scoring_guide.md"
            )
            scoring_guide = self.rubric_retriever.retrieve(
                "Data Engineering interview answer scoring guide score bands",
                source=scoring_guide_source,
            )
            retrieved.extend(scoring_guide)
        rubric_context = "\n\n".join(
            f"{'Scoring guide' if item.source.endswith('/scoring_guide.md') else 'Skill rubric'} "
            f"({item.skill}; source {item.source}):\n{item.text}"
            for item in retrieved
        )
        evaluation: EvaluationDetails = self.answer_evaluator.evaluate(
            request.question,
            request.answer,
            request.required_skills,
            request.job_description,
            rubric_context,
        )
        feedback = self.feedback_writer.write(
            evaluation,
            question=request.question,
            answer=request.answer,
            rubric_context=rubric_context,
        )
        return AnswerEvaluationResponse(
            score=evaluation.score,
            assessed_skills=evaluation.assessed_skills,
            matched_skills=evaluation.matched_skills,
            missing_skills=evaluation.missing_skills,
            feedback=feedback,
            sources=[
                EvaluationSource(skill=item.skill, source=item.source)
                for item in retrieved
            ],
            content_safe=evaluation.content_safe,
            confidence=evaluation.confidence,
            answer_relevant=evaluation.answer_relevant,
            skill_evidence=evaluation.skill_evidence,
            request_id=evaluation_request_id,
        )

    def transcribe_audio(
        self, audio: bytes, filename: str, content_type: str
    ) -> str:
        """Transcribe a voice answer through Groq without persisting the audio."""
        if self.mode != "groq":
            raise ValueError("Voice transcription requires Groq mode.")
        return GroqAudioTranscriber(self.settings).transcribe(
            audio,
            filename,
            content_type,
        )


def _is_data_engineering_role(job_description: str | None) -> bool:
    if not job_description:
        return False
    return (
        re.search(
            r"\bdata[\s-]+engineer(?:ing)?\b",
            job_description,
            re.IGNORECASE,
        )
        is not None
    )
