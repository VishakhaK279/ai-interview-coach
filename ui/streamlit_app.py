"""Streamlit demo for the AI Interview Coach API."""

import os

import requests
import streamlit as st

API_URL = os.getenv("INTERVIEW_API_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT_SECONDS = 15

st.set_page_config(page_title="AI Interview Coach", page_icon="🎤")
st.title("AI Interview Coach")
st.caption("Practice with a job description and get baseline, skill-focused feedback.")

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
        except requests.RequestException as exc:
            st.error(f"Could not reach the API at {API_URL}: {exc}")

questions = st.session_state.get("questions", [])
skills = st.session_state.get("skills", [])
if questions:
    if skills:
        st.write("Recognized role skills:", ", ".join(skills))
    else:
        st.info("No skills from the built-in catalog were recognized.")
    selected_question = st.selectbox("Choose a question", questions)
    answer = st.text_area("Your answer", height=160)
    if st.button("Evaluate answer"):
        if not answer.strip():
            st.warning("Write an answer first.")
        else:
            try:
                response = requests.post(
                    f"{API_URL}/interview/evaluate",
                    json={
                        "question": selected_question,
                        "answer": answer,
                        "required_skills": skills,
                    },
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                result = response.json()
                st.metric("Skill coverage score", f"{result['score']}%")
                st.write(result["feedback"])
            except requests.RequestException as exc:
                st.error(f"Could not reach the API at {API_URL}: {exc}")

st.caption("This demo uses deterministic keyword matching; it does not make LLM calls.")
