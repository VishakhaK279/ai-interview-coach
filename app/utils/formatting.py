"""Helpers for formatting evaluation results as candidate-facing feedback."""


def format_feedback(
    score: int,
    matched_skills: list[str],
    missing_skills: list[str],
) -> str:
    """Build concise feedback from skill coverage without claiming LLM analysis."""
    if not matched_skills and not missing_skills:
        return (
            "No role skills were provided for comparison. Include skills from the "
            "job description for more targeted feedback."
        )

    parts = [f"Your answer covered {score}% of the listed role skills."]
    if matched_skills:
        parts.append(f"Covered: {', '.join(matched_skills)}.")
    if missing_skills:
        parts.append(
            "Consider adding a specific example that demonstrates: "
            f"{', '.join(missing_skills)}."
        )
    return " ".join(parts)
