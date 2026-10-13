"""Orchestration for the interview-coaching agents."""

from app.agents.answer_evaluator import AnswerEvaluator
from app.agents.feedback_writer import FeedbackWriter
from app.agents.question_generator import QuestionGenerator
from app.models.schemas import (
    AnswerEvaluationRequest,
    AnswerEvaluationResponse,
    EvaluationDetails,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
)
from app.utils.jd_parser import extract_skills


class InterviewPipeline:
    """Coordinate independently replaceable agents for API workflows."""

    def __init__(
        self,
        question_generator: QuestionGenerator | None = None,
        answer_evaluator: AnswerEvaluator | None = None,
        feedback_writer: FeedbackWriter | None = None,
    ) -> None:
        self.question_generator = question_generator or QuestionGenerator()
        self.answer_evaluator = answer_evaluator or AnswerEvaluator()
        self.feedback_writer = feedback_writer or FeedbackWriter()

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
        self, request: AnswerEvaluationRequest
    ) -> AnswerEvaluationResponse:
        evaluation: EvaluationDetails = self.answer_evaluator.evaluate(
            request.question,
            request.answer,
            request.required_skills,
        )
        feedback = self.feedback_writer.write(evaluation)
        return AnswerEvaluationResponse(
            score=evaluation.score,
            matched_skills=evaluation.matched_skills,
            missing_skills=evaluation.missing_skills,
            feedback=feedback,
        )
