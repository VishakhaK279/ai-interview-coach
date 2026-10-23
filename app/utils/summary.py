"""Helpers for interview summary metrics and candidate report generation."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

EvaluationResult = Mapping[str, Any]
EVIDENCE_WEIGHTS = {
    "none": 0,
    "mention": 30,
    "example": 60,
    "detailed": 100,
}


def normalize_skill_score_details(value: Any) -> Mapping[str, int | str]:
    """Support legacy scalar scores while keeping their confidence conservative."""
    if isinstance(value, Mapping):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return {
            "score": value,
            "assessment_count": 1,
            "confidence": "Low confidence coverage (legacy score)",
        }
    raise TypeError(f"Unexpected skill score details: {type(value).__name__}")


def skill_evidence_scores(
    results: Iterable[EvaluationResult],
) -> dict[str, dict[str, int | str]]:
    """Return weighted evidence averages and assessment confidence per skill."""
    evidence_totals: dict[str, int] = defaultdict(int)
    assessed_counts: dict[str, int] = defaultdict(int)
    for result in results:
        if result.get("score") is None:
            continue

        evidence = result.get("skill_evidence")
        if not evidence:
            # Older session results only stored matched/missing lists.
            matched = set(result.get("matched_skills", []))
            evidence_by_skill = {
                skill: "mention" if skill in matched else "none"
                for skill in result.get("assessed_skills", [])
            }
        elif isinstance(evidence, list):
            evidence_by_skill = {
                item["skill"]: item["level"]
                for item in evidence
                if isinstance(item, Mapping)
                and item.get("level") in EVIDENCE_WEIGHTS
                and isinstance(item.get("skill"), str)
            }
        else:
            evidence_by_skill = {}

        for skill, level in evidence_by_skill.items():
            assessed_counts[skill] += 1
            evidence_totals[skill] += EVIDENCE_WEIGHTS[level]
    return {
        skill: {
            "score": round(evidence_totals[skill] / count),
            "assessment_count": count,
            "confidence": (
                "Low confidence coverage"
                if count == 1
                else "Building evidence"
                if count < 3
                else "Repeated evidence"
            ),
        }
        for skill, count in sorted(assessed_counts.items())
        if count
    }


def build_candidate_report(
    questions: list[str],
    results: Mapping[int, EvaluationResult],
) -> bytes:
    """Create a PDF with scores and coaching notes, excluding raw answers."""
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title="AI Interview Coach Candidate Report",
        author="AI Interview Coach",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17324D"),
        spaceAfter=8,
    )
    body_style = styles["BodyText"]
    section_style = styles["Heading2"]

    scored = [
        result for result in results.values() if result.get("score") is not None
    ]
    average = (
        round(sum(result["score"] for result in scored) / len(scored))
        if scored
        else None
    )
    strengths = sorted(
        {
            skill
            for result in scored
            for skill in result.get("matched_skills", [])
        }
    )
    improvement_areas = sorted(
        {
            skill
            for result in scored
            for skill in result.get("missing_skills", [])
        }
    )
    skill_scores = skill_evidence_scores(scored)
    skill_scores = {
        skill: normalize_skill_score_details(values)
        for skill, values in skill_scores.items()
    }

    story = [
        Paragraph("Interview Practice Report", title_style),
        Paragraph(
            f"Generated {datetime.now().astimezone().strftime('%B %d, %Y')}",
            ParagraphStyle(
                "ReportDate",
                parent=body_style,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#586575"),
            ),
        ),
        Spacer(1, 14),
        Paragraph("Overview", section_style),
        Paragraph(
            f"Questions evaluated: {len(results)} of {len(questions)}<br/>"
            f"Average score: {average}/100" if average is not None
            else f"Questions evaluated: {len(results)} of {len(questions)}<br/>"
            "Average score: Not available",
            body_style,
        ),
        Spacer(1, 8),
        Paragraph("Strengths", section_style),
        Paragraph(
            _list_text(strengths, "No skill evidence was marked as demonstrated."),
            body_style,
        ),
        Spacer(1, 6),
        Paragraph("Improvement areas", section_style),
        Paragraph(
            _list_text(
                improvement_areas,
                "No specific skill gaps were identified in scored answers.",
            ),
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Per-skill evidence scores", section_style),
        Paragraph(
            _list_text(
                [
                    f"{skill}: {values['score']}% "
                    f"({values['assessment_count']} assessment(s); "
                    f"{values['confidence']})"
                    for skill, values in skill_scores.items()
                ],
                "No per-skill scores are available.",
            ),
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Question-by-question feedback", section_style),
    ]

    table_data = [
        [
            Paragraph("<b>Question</b>", body_style),
            Paragraph("<b>Score</b>", body_style),
            Paragraph("<b>Feedback and review flag</b>", body_style),
        ]
    ]
    for index, question in enumerate(questions):
        result = results.get(index)
        if result is None:
            score_text = "Not evaluated"
            feedback = "No evaluation is available."
        elif result.get("score") is None:
            score_text = "Not scored"
            feedback = str(result.get("feedback", "No feedback is available."))
        else:
            score_text = f"{result['score']}/100"
            feedback = str(result.get("feedback", ""))
        if result is not None and result.get("confidence") == "low":
            feedback += "<br/><b>Low confidence — manual review needed.</b>"
        table_data.append(
            [
                Paragraph(escape(question), body_style),
                Paragraph(escape(score_text), body_style),
                Paragraph(escape(feedback).replace("\n", "<br/>"), body_style),
            ]
        )
    table = Table(table_data, colWidths=[2.55 * inch, 0.8 * inch, 3.05 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EAF0F6")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17324D")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C8D2DC")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)
    story.extend(
        [
            Spacer(1, 12),
            Paragraph(
                "Practice feedback is intended for learning and should not be used "
                "as a hiring decision.",
                styles["Italic"],
            ),
        ]
    )
    document.build(story)
    return buffer.getvalue()


def _list_text(values: list[str], empty_text: str) -> str:
    if not values:
        return escape(empty_text)
    return "<br/>".join(f"• {escape(value)}" for value in values)
