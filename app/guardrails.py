"""Shared candidate-facing guardrail behavior and audit logging."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("app.evaluation.audit")

NOT_SCORED_MESSAGE = "Answer not scored - irrelevant to the question"


def job_description_fingerprint(job_description: str | None) -> str | None:
    """Return a one-way identifier for audit correlation without logging the JD."""
    if not job_description:
        return None
    return hashlib.sha256(job_description.encode("utf-8")).hexdigest()


def log_evaluation(
    request_id: str,
    outcome: str,
    score: int | None,
    assessed_skills: list[str],
    sources: list[dict[str, str]],
    job_description: str | None,
    reason: str | None = None,
) -> None:
    """Write an audit event without candidate answers or raw job descriptions."""
    event: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "interview_evaluation",
        "request_id": request_id,
        "outcome": outcome,
        "score": score,
        "assessed_skills": assessed_skills,
        "sources": sources,
        "job_description_sha256": job_description_fingerprint(job_description),
    }
    if reason:
        event["reason"] = reason
    logger.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
