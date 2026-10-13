"""Local baseline agent for turning an evaluation into readable feedback."""

from app.models.schemas import EvaluationDetails
from app.utils.formatting import format_feedback


class FeedbackWriter:
    """Write concise feedback based on an answer evaluation."""

    def write(self, evaluation: EvaluationDetails) -> str:
        return format_feedback(
            evaluation.score,
            evaluation.matched_skills,
            evaluation.missing_skills,
        )
