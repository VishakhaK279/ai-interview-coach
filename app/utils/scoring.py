"""Deterministic baseline scoring helpers."""

import re


def score_answer(answer: str, required_skills: list[str]) -> tuple[int, list[str], list[str]]:
    """Score the share of distinct required skills mentioned in an answer."""
    skills = list(dict.fromkeys(skill.strip() for skill in required_skills if skill.strip()))
    answer_text = answer.casefold()
    matched = [
        skill
        for skill in skills
        if re.search(rf"(?<!\w){re.escape(skill.casefold())}(?!\w)", answer_text)
    ]
    missing = [skill for skill in skills if skill not in matched]
    score = round(100 * len(matched) / len(skills)) if skills else 0
    return score, matched, missing
