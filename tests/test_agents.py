import pytest

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

    assert evaluation.score == 100
    assert evaluation.assessed_skills == ["Python"]
    assert evaluation.matched_skills == ["Python"]
    assert evaluation.missing_skills == []


def test_feedback_writer_mentions_missing_skills() -> None:
    feedback = FeedbackWriter().write(
        EvaluationDetails(
            score=50,
            assessed_skills=["Python", "SQL"],
            matched_skills=["Python"],
            missing_skills=["SQL"],
        )
    )

    assert "50%" in feedback
    assert "SQL" in feedback


def test_question_generator_uses_injected_llm() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "Python" in user_prompt
            assert json_schema["properties"]["questions"]["type"] == "array"
            return '{"questions": ["Describe a Python project."]}'

    questions = QuestionGenerator(FakeChatClient()).generate("Python role", 1)

    assert questions == ["Describe a Python project."]


def test_answer_evaluator_uses_demonstrated_skill_evidence() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "country data" in user_prompt
            assert "Full job description" in user_prompt
            assert "ETL rubric says validate every load." in user_prompt
            assert "the only skills you may assess" in user_prompt
            assert '"Python", "SQL", "Cloud Platforms"' in user_prompt
            assert "one interview answer" in system_prompt
            assert "content_safe" in json_schema["properties"]
            assert json_schema["properties"]["answer_relevant"]["type"] == "boolean"
            assert json_schema["properties"]["score"]["type"] == "integer"
            assert json_schema["properties"]["confidence"]["enum"] == [
                "high",
                "medium",
                "low",
            ]
            return (
                '{"score": 75, "confidence": "high", "answer_relevant": true, '
                '"content_safe": true, '
                '"assessed_skills": ["Python", "SQL", "Cloud Platforms"], '
                '"skill_evidence": [{"skill": "Python", "level": "example"}, '
                '{"skill": "SQL", "level": "example"}, '
                '{"skill": "Cloud Platforms", "level": "none"}], '
                '"matched_skills": ["Python", "SQL"], '
                '"missing_skills": ["Cloud Platforms"]}'
            )

    evaluation = AnswerEvaluator(FakeChatClient()).evaluate(
        "Tell me about a project using Python, SQL, and AWS.",
        "I used Python to load country data into SQLite.",
        ["Python", "SQL", "Cloud Platforms"],
        "Use Python and SQL; AWS, GCP, or Azure experience is useful.",
        "ETL rubric says validate every load.",
    )

    assert evaluation.score == 75
    assert evaluation.confidence == "high"
    assert evaluation.answer_relevant is True
    assert evaluation.assessed_skills == ["Python", "SQL", "Cloud Platforms"]
    assert evaluation.matched_skills == ["Python", "SQL"]
    assert evaluation.missing_skills == ["Cloud Platforms"]


def test_answer_evaluator_does_not_penalize_skills_unrelated_to_question() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "Tell me about a project where you used Python" in user_prompt
            assert "Python" in user_prompt
            assert "SQL" in user_prompt
            assert "Git" in user_prompt
            return (
                '{"score": 78, "confidence": "medium", "answer_relevant": true, '
                '"content_safe": true, '
                '"assessed_skills": ["Python"], '
                '"skill_evidence": [{"skill": "Python", "level": "detailed"}], '
                '"matched_skills": ["Python"], "missing_skills": []}'
            )

    evaluation = AnswerEvaluator(FakeChatClient()).evaluate(
        "Tell me about a project where you used Python. What was your approach?",
        "I wrote a Python script to clean survey data, validated the output, and "
        "cut the weekly manual preparation from two hours to ten minutes.",
        ["Python", "SQL", "Git"],
        "The role requires Python, SQL, and Git.",
    )

    assert evaluation.score == 78
    assert evaluation.assessed_skills == ["Python"]
    assert evaluation.matched_skills == ["Python"]
    assert evaluation.missing_skills == []


def test_answer_evaluator_rejects_llm_assessing_skills_not_in_question() -> None:
    from app.llm.groq_client import GroqResponseError

    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "Alteryx" in user_prompt
            assert "Microsoft Fabric" in user_prompt
            return (
                '{"score": 5, "confidence": "medium", "answer_relevant": true, '
                '"content_safe": true, '
                '"assessed_skills": ["Python", "Git"], '
                '"skill_evidence": [{"skill": "Python", "level": "mention"}, '
                '{"skill": "Git", "level": "example"}], '
                '"matched_skills": ["Python", "Git"], "missing_skills": []}'
            )

    with pytest.raises(GroqResponseError, match="question-relevant"):
        AnswerEvaluator(FakeChatClient()).evaluate(
            "Can you describe your experience designing data pipelines using "
            "Alteryx and Microsoft Fabric?",
            "I only know Python and Git.",
            ["Python", "Git", "Alteryx", "Microsoft Fabric", "Data Pipelines"],
        )


def test_answer_evaluator_leaves_truly_off_topic_answer_unscored() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            return (
                '{"score": 5, "confidence": "low", "answer_relevant": false, '
                '"content_safe": true, '
                '"assessed_skills": [], '
                '"skill_evidence": [], '
                '"matched_skills": [], "missing_skills": []}'
            )

    evaluation = AnswerEvaluator(FakeChatClient()).evaluate(
        "Describe your experience with Alteryx.",
        "I only know Python and Git.",
        ["Alteryx", "Python", "Git"],
    )

    assert evaluation.score is None
    assert evaluation.assessed_skills == []
    assert evaluation.confidence == "low"
    assert evaluation.answer_relevant is False


def test_answer_evaluator_scores_relevant_answer_without_catalog_skill_match() -> None:
    question = (
        "How have you engineered and maintained data lakes or data warehouses to "
        "ensure high reliability, availability, and operational resilience, and "
        "what monitoring or fault-tolerance strategies did you implement?"
    )
    answer = (
        "In my current role at Amdocs, I work with SQL Server and an internal ETL "
        "framework to process data from multiple upstream applications and maintain "
        "data consistency. I ensure reliability through data validation, "
        "reconciliation checks, SQL query optimization, and systematic "
        "troubleshooting of production issues. I perform root cause analysis using "
        "logs and SQL queries to identify failures, investigate data discrepancies, "
        "and coordinate with upstream teams for resolution."
    )

    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "An empty skill list does not mean the answer is irrelevant." in user_prompt
            assert "root-cause analysis" in user_prompt
            assert "Question-relevant role skills (the only skills you may assess):\n[]" in user_prompt
            return (
                '{"score": 72, "confidence": "medium", "answer_relevant": true, '
                '"content_safe": true, "assessed_skills": [], '
                '"skill_evidence": [], '
                '"matched_skills": [], "missing_skills": []}'
            )

    evaluation = AnswerEvaluator(FakeChatClient()).evaluate(
        question,
        answer,
        ["SQL", "ETL", "Troubleshooting", "Data Pipelines"],
    )

    assert evaluation.score == 72
    assert evaluation.answer_relevant is True
    assert evaluation.assessed_skills == []
    assert evaluation.matched_skills == []
    assert evaluation.missing_skills == []


def test_answer_evaluator_recovers_skill_mentions_from_false_irrelevance() -> None:
    question = (
        "Can you describe a recent project where you designed and implemented a "
        "high-performance data processing pipeline using Python/Scala and Apache "
        "Spark, including how you identified and resolved performance bottlenecks "
        "and ensured low latency?"
    )
    answer = (
        "I develop and optimize ETL workflows using JavaScript, an internal ETL "
        "framework, and SQL Server. I improve performance by optimizing SQL queries "
        "and investigating processing bottlenecks. I use SQL queries and log "
        "analysis to identify discrepancies and troubleshoot issues. My professional "
        "experience is primarily with traditional ETL technologies; I am building "
        "my skills in Python and Apache Spark."
    )

    class FalseNegativeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            return (
                '{"score": 0, "confidence": "low", "answer_relevant": false, '
                '"content_safe": true, "assessed_skills": [], "skill_evidence": [], '
                '"matched_skills": [], "missing_skills": []}'
            )

    evaluation = AnswerEvaluator(FalseNegativeChatClient()).evaluate(
        question,
        answer,
        ["Python", "Apache Spark", "SQL", "ETL"],
    )

    assert evaluation.score == 30
    assert evaluation.answer_relevant is True
    assert evaluation.confidence == "low"
    assert evaluation.assessed_skills == ["Python", "Apache Spark"]
    assert evaluation.matched_skills == ["Python", "Apache Spark"]
    assert evaluation.missing_skills == []
    assert [item.level for item in evaluation.skill_evidence] == [
        "mention",
        "mention",
    ]


def test_answer_evaluator_blocks_unsafe_content_without_repeating_it() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            return (
                '{"score": 0, "confidence": "low", "answer_relevant": false, '
                '"content_safe": false, '
                '"assessed_skills": [], '
                '"skill_evidence": [], '
                '"matched_skills": [], "missing_skills": []}'
            )

    evaluation = AnswerEvaluator(FakeChatClient()).evaluate(
        "Describe your Python experience.",
        "unsafe candidate content",
        ["Python"],
    )

    assert evaluation.score is None
    assert evaluation.content_safe is False
    assert evaluation.confidence == "low"
    assert evaluation.answer_relevant is False
    assert evaluation.assessed_skills == []


def test_answer_evaluator_returns_unscored_when_question_has_no_role_skill() -> None:
    evaluation = AnswerEvaluator().evaluate(
        "Tell me about a challenge you overcame.",
        "I organized a community event.",
        ["Python", "SQL"],
    )

    assert evaluation.score is None
    assert evaluation.assessed_skills == []
    assert evaluation.confidence == "low"


def test_feedback_writer_uses_injected_llm() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "What was your approach and what was the result?" in user_prompt
            assert "I cleaned event data using Python and reduced processing time." in user_prompt
            assert "assessed_skills" in user_prompt
            return "Good example; explain the outcome with a metric."

    feedback = FeedbackWriter(FakeChatClient()).write(
        EvaluationDetails(
            score=80,
            assessed_skills=["Python"],
            matched_skills=["Python"],
            missing_skills=[],
        ),
        question="What was your approach and what was the result?",
        answer="I cleaned event data using Python and reduced processing time.",
    )

    assert feedback == "Good example; explain the outcome with a metric."


def test_feedback_writer_generates_feedback_when_no_catalog_skill_was_assessed() -> None:
    class FakeChatClient:
        def complete(
            self, system_prompt: str, user_prompt: str, json_schema=None
        ) -> str:
            assert "data platform reliability" in user_prompt
            assert "SQL query optimization" in user_prompt
            return "Your validation and troubleshooting examples address reliability."

    feedback = FeedbackWriter(FakeChatClient()).write(
        EvaluationDetails(
            score=72,
            confidence="medium",
            answer_relevant=True,
            assessed_skills=[],
            matched_skills=[],
            missing_skills=[],
        ),
        question="How do you ensure data platform reliability?",
        answer="I use SQL query optimization and troubleshooting.",
    )

    assert "address reliability" in feedback
