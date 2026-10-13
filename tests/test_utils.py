from app.utils.formatting import format_feedback
from app.utils.jd_parser import extract_skills
from app.utils.scoring import score_answer


def test_extract_skills_finds_catalog_terms_without_partial_matches() -> None:
    assert extract_skills("Python, SQL and machine learning; not pythonic.") == [
        "Python",
        "SQL",
        "Machine Learning",
    ]


def test_score_answer_is_case_insensitive_and_deduplicates_skills() -> None:
    assert score_answer("I use python.", ["Python", "Python", "SQL"]) == (
        50,
        ["Python"],
        ["SQL"],
    )


def test_format_feedback_handles_missing_comparison_skills() -> None:
    feedback = format_feedback(0, [], [])

    assert "No role skills" in feedback
