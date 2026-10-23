"""Turn an answer evaluation into candidate-facing feedback."""

from app.llm.groq_client import ChatClient
from app.guardrails import NOT_SCORED_MESSAGE
from app.models.schemas import EvaluationDetails
from app.utils.formatting import format_feedback


class FeedbackWriter:
    """Write candidate-facing feedback locally or through a chat model."""

    def __init__(self, llm_client: ChatClient | None = None) -> None:
        self.llm_client = llm_client

    def write(
        self,
        evaluation: EvaluationDetails,
        question: str | None = None,
        answer: str | None = None,
        rubric_context: str | None = None,
    ) -> str:
        if evaluation.score is None:
            return NOT_SCORED_MESSAGE
        if self.llm_client is not None:
            return self.llm_client.complete(
                "You are a supportive interview coach. Give feedback grounded "
                "strictly in the supplied question and candidate answer. Never "
                "claim the candidate used a language, tool, query, or technique "
                "unless the answer provides evidence for it. Keep feedback "
                "professional, constructive, respectful, and non-discriminatory. "
                "Do not criticize grammar, accent, or answer length.",
                (
                    "Write concise, specific feedback for this one response. "
                    "Explain what the candidate actually did well and give one or "
                    "two improvements tied to the question. Do not provide generic "
                    "advice unrelated to the answer, invent details, or criticize "
                    "missing skills not listed as assessed. If evidence for a skill "
                    "is absent, describe it as an opportunity rather than claiming "
                    "the candidate demonstrated it. Do not suggest they falsely "
                    "claim experience.\n\n"
                    f"Question:\n{question or 'Not provided'}\n\n"
                    f"Candidate answer:\n{answer or 'Not provided'}\n\n"
                    f"Evaluation:\n{evaluation.model_dump_json(indent=2)}\n\n"
                    f"Relevant rubric context:\n{rubric_context or 'Not provided'}"
                ),
            )
        return format_feedback(
            evaluation.score,
            evaluation.matched_skills,
            evaluation.missing_skills,
        )
