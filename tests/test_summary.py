from app.utils.summary import build_candidate_report, skill_evidence_scores


def test_skill_evidence_scores_ignore_unscored_responses() -> None:
    results = [
        {
            "score": 80,
            "assessed_skills": ["Python", "SQL"],
            "matched_skills": ["Python"],
            "skill_evidence": [
                {"skill": "Python", "level": "mention"},
                {"skill": "SQL", "level": "none"},
            ],
        },
        {
            "score": 70,
            "assessed_skills": ["Python"],
            "matched_skills": ["Python"],
            "skill_evidence": [{"skill": "Python", "level": "example"}],
        },
        {
            "score": None,
            "assessed_skills": ["SQL"],
            "matched_skills": [],
            "skill_evidence": [{"skill": "SQL", "level": "detailed"}],
        },
    ]

    assert skill_evidence_scores(results) == {
        "Python": {
            "score": 45,
            "assessment_count": 2,
            "confidence": "Building evidence",
        },
        "SQL": {
            "score": 0,
            "assessment_count": 1,
            "confidence": "Low confidence coverage",
        },
    }


def test_single_detailed_answer_is_low_confidence_and_repeated_evidence_builds() -> None:
    results = [
        {
            "score": 80,
            "assessed_skills": ["Python"],
            "matched_skills": ["Python"],
            "skill_evidence": [{"skill": "Python", "level": "detailed"}],
        },
        {
            "score": 75,
            "assessed_skills": ["Python"],
            "matched_skills": ["Python"],
            "skill_evidence": [{"skill": "Python", "level": "example"}],
        },
        {
            "score": 85,
            "assessed_skills": ["Python"],
            "matched_skills": ["Python"],
            "skill_evidence": [{"skill": "Python", "level": "detailed"}],
        },
    ]

    score = skill_evidence_scores(results)["Python"]

    assert score == {
        "score": 87,
        "assessment_count": 3,
        "confidence": "Repeated evidence",
    }


def test_candidate_pdf_contains_summary_but_not_raw_answers() -> None:
    pdf = build_candidate_report(
        ["Tell me about Python."],
        {
            0: {
                "score": 80,
                "confidence": "low",
                "assessed_skills": ["Python"],
                "matched_skills": ["Python"],
                "skill_evidence": [{"skill": "Python", "level": "detailed"}],
                "missing_skills": [],
                "feedback": "Explain the result clearly.",
                "answer": "PRIVATE raw candidate answer",
            }
        },
    )

    assert pdf.startswith(b"%PDF-")
    assert b"PRIVATE raw candidate answer" not in pdf
