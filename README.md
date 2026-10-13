# AI Interview Coach

A starter project for practicing interview questions against a job description. The API, three independently replaceable agents, orchestration pipeline, Streamlit demo, and tests have clear boundaries so teammates can work on separate modules.

## What is included

- A FastAPI backend with question-generation and answer-evaluation endpoints.
- Three deterministic local agents: question generator, answer evaluator, and feedback writer.
- Job-description skill extraction, scoring, and feedback formatting helpers.
- A Streamlit demo that calls the backend.
- Tests for the agents, pipeline, and utilities.

The local agents are a working baseline, not an LLM-powered evaluator. They use a small built-in skill list and keyword matching. There are no API keys to configure and no external model calls. LangGraph is included for teammates who want to move orchestration into a graph; the starter pipeline currently uses direct Python calls. Teammates can replace an agent's implementation while keeping its input/output contract stable.

## Setup

Use Python 3.10 or newer. From this directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use the environment's Python executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the app

Start the API in one terminal:

```powershell
python -m uvicorn app.main:app --reload
```

Open the API docs at <http://127.0.0.1:8000/docs>.

Start the demo in a second terminal:

```powershell
python -m streamlit run ui/streamlit_app.py
```

The demo expects the API at `http://127.0.0.1:8000`. To use a different URL, set the `INTERVIEW_API_URL` environment variable before starting Streamlit.
If you did not activate the virtual environment, replace `python` with `.\.venv\Scripts\python.exe` in the commands above.

## API quick reference

- `GET /health` — check that the API is running.
- `POST /interview/questions` — JSON body: `{"job_description": "...", "question_count": 5}`.
- `POST /interview/evaluate` — JSON body: `{"question": "...", "answer": "...", "required_skills": ["Python", "SQL"]}`.

Question generation extracts recognized skills from the job description. Pass those skills as `required_skills` when evaluating an answer; the UI does this automatically.

## Tests

```powershell
python -m pytest
```

## Team ownership and contracts

Suggested independent work areas:

- **Question generation:** `app/agents/question_generator.py`. Keep `generate(job_description, question_count)` returning a list of question strings.
- **Answer evaluation:** `app/agents/answer_evaluator.py` and `app/utils/scoring.py`. Keep `evaluate(question, answer, required_skills)` returning `EvaluationDetails`.
- **Feedback:** `app/agents/feedback_writer.py` and `app/utils/formatting.py`. Keep `write(evaluation)` returning a string.
- **Integration/API:** `app/pipelines/interview_pipeline.py` and `app/main.py`.
- **Demo UI:** `ui/streamlit_app.py`.

Agree on contract changes with the integration owner before changing schemas. Create a feature branch per task, run `pytest` before opening a pull request, and avoid committing `.env` files or credentials.

## Configuration and screenshots

`config.yaml` contains non-secret defaults for the app and local agent behavior. Do not put API keys in it. If an LLM provider is added later, read credentials from environment variables and document required variable names here.

There are no demo screenshots yet; add them here when a hosted or local demo is available.
