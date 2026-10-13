from app.agents.answer_evaluator import AnswerEvaluator
from app.agents.feedback_writer import FeedbackWriter
from app.agents.question_generator import QuestionGenerator
from app.models.schemas import EvaluationDetails


def test_question_generator_uses_recognized_skills() -> None:
    questions = QuestionGenerator().generate(
        "We need Python and SQL experience.", question_count=1
    )

    assert len(questions) == 1
    assert "Python" in questions[0]


def test_answer_evaluator_scores_skill_coverage() -> None:
    evaluation = AnswerEvaluator().evaluate(
        "How do you use Python?",
        "I used Python to automate reporting.",
        ["Python", "SQL"],
    )

    assert evaluation.score == 50
    assert evaluation.matched_skills == ["Python"]
    assert evaluation.missing_skills == ["SQL"]


def test_feedback_writer_mentions_missing_skills() -> None:
    feedback = FeedbackWriter().write(
        EvaluationDetails(score=50, matched_skills=["Python"], missing_skills=["SQL"])
    )

    assert "50%" in feedback
    assert "SQL" in feedback
