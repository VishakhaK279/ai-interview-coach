"""Local baseline agent for generating role-specific interview questions."""

from app.utils.jd_parser import extract_skills


class QuestionGenerator:
    """Generate interview questions from recognized job-description skills."""

    def generate(self, job_description: str, question_count: int = 5) -> list[str]:
        skills = extract_skills(job_description)
        questions = [
            f"Tell me about a project where you used {skill}. What was your approach and what was the result?"
            for skill in skills
        ]
        if not questions:
            questions = [
                "What experience makes you a good fit for this role?",
                "Tell me about a challenging project and how you handled it.",
                "How do you approach learning an unfamiliar tool or process?",
            ]
        return questions[:question_count]
