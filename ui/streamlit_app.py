"""Streamlit demo for the AI Interview Coach API."""

import hashlib
import os
from collections.abc import Mapping
from uuid import uuid4

import requests
import streamlit as st
import plotly.graph_objects as go

from app.utils.summary import (
    build_candidate_report,
    normalize_skill_score_details,
    skill_evidence_scores,
)

API_URL = os.getenv("INTERVIEW_API_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("INTERVIEW_API_TIMEOUT_SECONDS", "120"))


def request_error_message(error: requests.RequestException) -> str:
    """Show API error details when the server responded."""
    if isinstance(error, requests.ReadTimeout):
        return (
            "The API did not finish before the client timeout. Groq transcription "
            "and RAG evaluation can take longer; the request may still be processing. "
            "Increase INTERVIEW_API_TIMEOUT_SECONDS if needed."
        )
    if isinstance(error, requests.ConnectTimeout):
        return f"Could not establish a connection to the API at {API_URL} in time."
    response = error.response
    if response is None:
        return f"Could not reach the API at {API_URL}: {error}"

    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and isinstance(payload.get("detail"), str):
        return payload["detail"]
    return f"API returned HTTP {response.status_code}: {response.text}"


st.set_page_config(page_title="AI Interview Coach", page_icon="🎤")
st.title("AI Interview Coach")
st.caption("Generate tailored interview questions and get role-focused answer feedback.")

uploaded_file = st.file_uploader("Upload a job description (.txt)", type=["txt"])
job_description = st.text_area(
    "Or paste the job description",
    value=uploaded_file.getvalue().decode("utf-8", errors="replace")
    if uploaded_file
    else "",
    height=180,
)
question_count = st.slider("Number of questions", min_value=1, max_value=10, value=5)

if st.button("Generate questions", type="primary"):
    if not job_description.strip():
        st.warning("Add a job description first.")
    else:
        try:
            with st.spinner("Generating questions with the configured model..."):
                response = requests.post(
                    f"{API_URL}/interview/questions",
                    json={
                        "job_description": job_description,
                        "question_count": question_count,
                    },
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            response.raise_for_status()
            result = response.json()
            st.session_state["questions"] = result["questions"]
            st.session_state["skills"] = result["skills"]
            st.session_state["job_description"] = job_description
            st.session_state["question_index"] = 0
            st.session_state["evaluation_results"] = {}
            st.session_state["interview_id"] = uuid4().hex
            st.session_state["show_summary"] = False
        except requests.RequestException as exc:
            st.error(request_error_message(exc))

questions = st.session_state.get("questions", [])
skills = st.session_state.get("skills", [])
if questions:
    question_index = st.session_state.get("question_index", 0)
    evaluation_results = st.session_state.setdefault("evaluation_results", {})
    interview_id = st.session_state.setdefault("interview_id", uuid4().hex)
    answer_key = f"answer_{interview_id}_{question_index}"

    if st.session_state.get("show_summary", False):
        st.header("Interview summary")
        scored_results = [
            result
            for result in evaluation_results.values()
            if result.get("score") is not None
        ]
        if scored_results:
            average_score = round(
                sum(result["score"] for result in scored_results)
                / len(scored_results)
            )
            st.metric("Average score", f"{average_score}/100")
        else:
            st.info("No questions received a score.")
        st.caption(
            f"Evaluated {len(evaluation_results)} of {len(questions)} questions."
        )

        skill_scores = skill_evidence_scores(evaluation_results.values())
        if skill_scores:
            st.subheader("Skill evidence dashboard")
            skill_details: dict[str, Mapping[str, int | str]] = {}
            for name, value in skill_scores.items():
                try:
                    skill_details[name] = normalize_skill_score_details(value)
                except TypeError as exc:
                    raise TypeError(f"Invalid score details for {name!r}") from exc

            skill_names = list(skill_details)
            evidence_values = [
                int(skill_details[name]["score"]) for name in skill_names
            ]
            assessment_counts = [
                int(skill_details[name]["assessment_count"]) for name in skill_names
            ]
            confidence_labels = [
                str(skill_details[name]["confidence"]) for name in skill_names
            ]
            bar_colors = [
                "#9BC7DD" if count == 1 else "#2E86AB"
                for count in assessment_counts
            ]

            st.info(
                "This is evidence from your answers, not a measure of your overall "
                "skill. 30% = skill mentioned, 60% = example given, and 100% = "
                "detailed explanation. Scores are averaged across questions that "
                "assessed each skill. Pale bars mean only one question assessed it."
            )
            bar_chart = go.Figure(
                go.Bar(
                    x=evidence_values,
                    y=skill_names,
                    orientation="h",
                    marker_color=bar_colors,
                    customdata=list(zip(assessment_counts, confidence_labels)),
                    text=[f"{score}%" for score in evidence_values],
                    textposition="outside",
                    hovertemplate=(
                        "%{y}: %{x}% answer evidence<br>"
                        "Assessed in %{customdata[0]} question(s)<br>"
                        "%{customdata[1]}<extra></extra>"
                    ),
                )
            )
            bar_chart.update_layout(
                title="Evidence shown in your answers",
                xaxis_title="Answer evidence (%) — not skill proficiency",
                yaxis_title="",
                xaxis_range=[0, 110],
                margin={"t": 55, "b": 25, "l": 110},
            )
            st.plotly_chart(
                bar_chart,
                use_container_width=True,
                key="skill-evidence-bar-chart",
            )

            st.markdown(
                "**How to use this:** Candidates can see which answers may need "
                "a clearer example; interviewers can use it to choose follow-up "
                "questions. It is not a hiring recommendation or proof of ability."
            )
            stronger_evidence = [
                skill
                for skill in skill_names
                if int(skill_details[skill]["score"]) >= 60
            ]
            more_detail = [
                skill
                for skill in skill_names
                if int(skill_details[skill]["score"]) < 60
            ]
            evidence_col, detail_col = st.columns(2)
            with evidence_col:
                st.markdown("**Answers with examples or detailed evidence**")
                if stronger_evidence:
                    st.markdown(
                        "\n".join(
                            f"- **{skill}** — {skill_details[skill]['score']}% "
                            f"answer evidence"
                            for skill in stronger_evidence
                        )
                    )
                else:
                    st.caption(
                        "No assessed answer reached the example-evidence level yet."
                    )
            with detail_col:
                st.markdown("**Answers that could use more detail**")
                if more_detail:
                    st.markdown(
                        "\n".join(
                            f"- **{skill}** — {skill_details[skill]['score']}% "
                            "answer evidence"
                            for skill in more_detail
                        )
                    )
                else:
                    st.caption(
                        "Every assessed answer included at least example-level "
                        "evidence."
                    )
            st.dataframe(
                [
                    {
                        "Skill": skill,
                        "Weighted evidence": f"{skill_details[skill]['score']}%",
                        "Assessed questions": skill_details[skill][
                            "assessment_count"
                        ],
                        "Coverage confidence": skill_details[skill]["confidence"],
                    }
                    for skill in skill_names
                ],
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Skill charts will appear after at least one answer is scored.")

        st.download_button(
            "Download candidate report (PDF)",
            data=build_candidate_report(questions, evaluation_results),
            file_name="interview-practice-report.pdf",
            mime="application/pdf",
            key="candidate-report-download",
        )

        for index, question in enumerate(questions):
            result = evaluation_results.get(index)
            title = f"Question {index + 1}"
            if result is None:
                st.warning(f"{title}: Not evaluated")
                continue
            if result.get("score") is None:
                st.write(f"**{title}:** Not scored")
            else:
                st.write(f"**{title}:** {result['score']}/100")
            with st.expander(question):
                st.write(f"**Your answer:** {result.get('answer', '')}")
                if result.get("score") is None:
                    st.info(result["feedback"])
                else:
                    st.write(result["feedback"])
                if result.get("confidence") == "low":
                    st.warning("Low confidence — manual review needed.")
                assessed_skills = result.get("assessed_skills", [])
                if assessed_skills:
                    st.caption("Skills assessed: " + ", ".join(assessed_skills))

        if st.button("Back to questions"):
            st.session_state["show_summary"] = False
            st.rerun()
    else:
        if skills:
            st.write("Recognized role skills:", ", ".join(skills))
        else:
            st.info("No skills from the built-in catalog were recognized.")

        st.subheader(f"Question {question_index + 1} of {len(questions)}")
        selected_question = questions[question_index]
        st.write(selected_question)
        st.caption(
            "When you stop recording, your answer is automatically transcribed with "
            "Groq and placed in the answer box for review. The audio is not stored "
            "by this app."
        )
        audio_recording = st.audio_input(
            "Record your answer",
            key=f"audio_{interview_id}_{question_index}",
        )
        transcription_state_key = (
            f"transcription_{interview_id}_{question_index}"
        )
        if audio_recording is not None:
            audio_bytes = audio_recording.getvalue()
            recording_fingerprint = hashlib.sha256(audio_bytes).hexdigest()
            transcription_state = st.session_state.get(
                transcription_state_key, {}
            )
            if transcription_state.get("fingerprint") != recording_fingerprint:
                st.session_state[transcription_state_key] = {
                    "fingerprint": recording_fingerprint,
                    "status": "transcribing",
                }
                try:
                    with st.spinner("Transcribing your answer..."):
                        response = requests.post(
                            f"{API_URL}/interview/transcribe",
                            data=audio_bytes,
                            headers={
                                "Content-Type": audio_recording.type
                                or "application/octet-stream",
                                "X-Audio-Filename": audio_recording.name
                                or "answer.wav",
                            },
                            timeout=REQUEST_TIMEOUT_SECONDS,
                        )
                    response.raise_for_status()
                    transcript = response.json()["text"]
                    if not isinstance(transcript, str) or not transcript.strip():
                        raise ValueError(
                            "Transcription returned no text. Record your answer again."
                        )
                    st.session_state[answer_key] = transcript.strip()
                    st.session_state[transcription_state_key] = {
                        "fingerprint": recording_fingerprint,
                        "status": "complete",
                    }
                    st.rerun()
                except requests.RequestException as exc:
                    st.session_state[transcription_state_key] = {
                        "fingerprint": recording_fingerprint,
                        "status": "error",
                        "message": request_error_message(exc),
                    }
                except (KeyError, TypeError, ValueError):
                    st.session_state[transcription_state_key] = {
                        "fingerprint": recording_fingerprint,
                        "status": "error",
                        "message": (
                            "The transcription response did not contain valid text. "
                            "Please record your answer again."
                        ),
                    }

            transcription_state = st.session_state[transcription_state_key]
            if transcription_state["status"] == "complete":
                st.success("Transcription complete. Review it before evaluation.")
            elif transcription_state["status"] == "error":
                st.error(transcription_state["message"])
                if st.button(
                    "Retry transcription",
                    key=f"retry_transcription_{interview_id}_{question_index}",
                ):
                    st.session_state.pop(transcription_state_key, None)
                    st.rerun()

        answer = st.text_area(
            "Your answer",
            height=160,
            key=answer_key,
        )

        if st.button("Evaluate answer", type="primary"):
            if not answer.strip():
                st.warning("Write your answer first.")
            else:
                try:
                    with st.spinner(
                        "Retrieving references and evaluating your answer..."
                    ):
                        response = requests.post(
                            f"{API_URL}/interview/evaluate",
                            json={
                                "question": selected_question,
                                "answer": answer,
                                "required_skills": skills,
                                "job_description": st.session_state.get(
                                    "job_description", ""
                                ),
                            },
                            timeout=REQUEST_TIMEOUT_SECONDS,
                        )
                    response.raise_for_status()
                    result = response.json()
                    result["answer"] = answer
                    evaluation_results[question_index] = result
                    st.session_state["evaluation_results"] = evaluation_results
                    st.rerun()
                except requests.RequestException as exc:
                    st.error(request_error_message(exc))

        saved_result = evaluation_results.get(question_index)
        if saved_result is not None:
            st.divider()
            if saved_result["score"] is None:
                st.info(saved_result["feedback"])
            else:
                st.metric("Evaluation score", f"{saved_result['score']}/100")
                st.write(saved_result["feedback"])
            if saved_result.get("confidence") == "low":
                st.warning("Low confidence — manual review needed.")
            if not saved_result.get("content_safe", True):
                st.warning(
                    "This response was not scored by the content-safety guardrail."
                )
            assessed_skills = saved_result.get("assessed_skills", [])
            if assessed_skills and saved_result["score"] is not None:
                st.caption(
                    "Skills assessed for this question: "
                    + ", ".join(assessed_skills)
                )

        previous_col, next_col = st.columns(2)
        with previous_col:
            if st.button("Previous question", disabled=question_index == 0):
                st.session_state["question_index"] = question_index - 1
                st.rerun()
        with next_col:
            is_last_question = question_index == len(questions) - 1
            if is_last_question:
                all_evaluated = len(evaluation_results) == len(questions)
                if st.button(
                    "Finish and view summary",
                    disabled=not all_evaluated,
                ):
                    st.session_state["show_summary"] = True
                    st.rerun()
                if not all_evaluated:
                    st.caption(
                        "Evaluate every question to finish. Use Previous question "
                        "to return to any unanswered question."
                    )
            elif st.button("Next question"):
                st.session_state["question_index"] = question_index + 1
                st.rerun()

st.caption(
    "Groq mode uses an LLM for questions and feedback. Local mode uses deterministic "
    "keyword matching and does not provide reliable content-safety moderation."
)
