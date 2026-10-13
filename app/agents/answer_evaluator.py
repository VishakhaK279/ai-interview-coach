"""Local baseline agent for evaluating an answer against role skills."""

from app.models.schemas import EvaluationDetails
from app.utils.scoring import score_answer


class AnswerEvaluator:
    """Score an answer using keyword coverage of the supplied skills."""

    def evaluate(
        self,
        question: str,
        answer: str,
        required_skills: list[str],
    ) -> EvaluationDetails:
        del question  # The local baseline scores skill coverage, not question relevance.
        score, matched_skills, missing_skills = score_answer(answer, required_skills)
        return EvaluationDetails(
            score=score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )
