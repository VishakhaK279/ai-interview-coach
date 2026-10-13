"""Utilities for extracting a small set of known skills from job descriptions."""

import re

SKILL_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Python", ("python",)),
    ("Java", ("java",)),
    ("JavaScript", ("javascript", "js")),
    ("TypeScript", ("typescript",)),
    ("SQL", ("sql",)),
    ("FastAPI", ("fastapi",)),
    ("Django", ("django",)),
    ("Flask", ("flask",)),
    ("React", ("react",)),
    ("Node.js", ("node.js", "nodejs")),
    ("AWS", ("aws", "amazon web services")),
    ("Azure", ("azure",)),
    ("Docker", ("docker",)),
    ("Kubernetes", ("kubernetes",)),
    ("Machine Learning", ("machine learning",)),
    ("Deep Learning", ("deep learning",)),
    ("Data Analysis", ("data analysis", "data analytics")),
    ("Communication", ("communication",)),
    ("Leadership", ("leadership",)),
    ("Project Management", ("project management",)),
    ("Git", ("git",)),
    ("REST APIs", ("rest api", "rest apis")),
    ("LangGraph", ("langgraph",)),
)


def extract_skills(job_description: str) -> list[str]:
    """Return recognized skills in their order of appearance in the catalog."""
    text = job_description.casefold()
    skills: list[str] = []
    for skill, aliases in SKILL_ALIASES:
        if any(
            re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text)
            for alias in aliases
        ):
            skills.append(skill)
    return skills
