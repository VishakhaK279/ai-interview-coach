"""Generate role-specific interview questions."""

import json
from typing import cast

from app.llm.groq_client import ChatClient, GroqResponseError
from app.utils.jd_parser import extract_skills


class QuestionGenerator:
    """Generate role-specific questions locally or through a chat model."""

    def __init__(self, llm_client: ChatClient | None = None) -> None:
        self.llm_client = llm_client

    def generate(self, job_description: str, question_count: int = 5) -> list[str]:
        if self.llm_client is not None:
            response = self.llm_client.complete(
                "You create practical interview questions based on job descriptions. "
                "Return only valid JSON with a 'questions' array of strings.",
                (
                    f"Generate exactly {question_count} distinct interview questions "
                    "for this job description. Cover its responsibilities and "
                    "requirements. Return JSON only, shaped as "
                    '{"questions": ["..."]}.\n\n'
                    f"Job description:\n{job_description}"
                ),
                json_schema={
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "items": {"type": "string"},
                        }
                    },
                    "required": ["questions"],
                    "additionalProperties": False,
                },
            )
            try:
                payload = json.loads(response)
                questions = payload["questions"]
            except (ValueError, KeyError, TypeError) as exc:
                raise GroqResponseError(
                    "Question-generation response was not valid JSON with a "
                    "'questions' array."
                ) from exc
            if (
                not isinstance(questions, list)
                or len(questions) != question_count
                or any(not isinstance(question, str) or not question.strip() for question in questions)
            ):
                raise GroqResponseError(
                    "Question-generation response must contain exactly the requested "
                    "number of non-empty question strings."
                )
            return cast(list[str], questions[:question_count])

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
