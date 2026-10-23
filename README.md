# AI Interview Coach

A starter project for practicing interview questions against a job description. The API, three independently replaceable agents, orchestration pipeline, Streamlit demo, and tests have clear boundaries so teammates can work on separate modules.

## What is included

- A FastAPI backend with question-generation and answer-evaluation endpoints.
- Three agents: question generator, answer evaluator, and feedback writer. Groq is enabled by default; deterministic local implementations remain available.
- Job-description skill extraction, scoring, and feedback formatting helpers.
- A Streamlit demo with sequential questions, voice transcription, charts, and PDF export.
- Tests for the agents, pipeline, and utilities.

The default agents make Groq chat-completion calls. The evaluator intersects recognized skills in the selected question with recognized role skills from the job description and rejects LLM skill classifications outside that intersection. This maintained phrase catalog is not a complete semantic model: if no role skill matches a question, Groq still evaluates whether the answer substantively addresses the question instead of automatically marking it irrelevant. A relevant but incomplete answer receives a score; genuinely off-topic answers remain unscored. The API reports `answer_relevant` separately from recognized-skill coverage. Local mode remains a deterministic keyword-matching baseline and cannot semantically assess questions that have no recognized skill match, so those answers are marked low-confidence and unscored. Feedback receives the original question and answer so its coaching is grounded in the specific response. LangGraph is included for teammates who want to move orchestration into a graph; the starter pipeline currently uses direct Python calls. Teammates can replace an agent's implementation while keeping its input/output contract stable.

The Data Engineer evaluator uses local RAG: the role rubrics and benchmark Q&A in `data/rubrics/data_engineering/` are chunked and indexed in Chroma, embedded with Ollama, retrieved for Data Engineer job descriptions, and passed to Groq as evaluation context. The full `scoring_guide.md` is retrieved by source so all of its score bands are available to the evaluator. The rubric text is versioned in Git; the generated vector index is local and ignored by Git.

## Evaluation guardrails and audit trail

Guardrail behavior is implemented in `app/agents/answer_evaluator.py` (question relevance, style-neutral scoring, and Groq-mode content safety), `app/agents/feedback_writer.py` (evidence-grounded, respectful feedback), `app/pipelines/interview_pipeline.py` (no-score handling), and `app/guardrails.py` (fallback text and audit event format). If evaluation fails or no listed skill is relevant to the question, the API returns a null score and `Answer not scored - irrelevant to the question`. API evaluation responses include a `request_id` (also sent as `X-Request-ID`), `assessed_skills`, and retrieved source references for troubleshooting and integration. The Streamlit candidate view omits request IDs and source file paths.

Evaluation audit events are emitted as structured JSON to the application log. The API logs to its console and to `logs/app.log` under the project root. The log file rotates at 5 MB and keeps three backups (`app.log.1`, etc.); `logs/` is excluded from Git. Events include the request ID, timestamp, outcome, score, assessed skills, source paths, and a SHA-256 fingerprint of the job description; raw answers and raw job descriptions are not logged. The SHA-256 fingerprint is a correlation identifier, not anonymization. For deployment, configure a log collector and retention policy appropriate to your privacy requirements.

Typed and transcribed voice answers use the same text evaluation endpoint. Groq mode asks the evaluator to block hateful, discriminatory, threatening, or abusive answers without repeating them in feedback. This model-based moderation is a guardrail, not a guarantee. Local mode is only a deterministic development baseline and does **not** provide reliable content-safety moderation; do not expose it as a public evaluation service. Scores are practice feedback, not hiring decisions, and the system is instructed not to judge grammar, accent, writing style, or verbosity.

When the evaluator marks its confidence as low, the UI displays **“Low confidence — manual review needed.”** Local keyword-matching evaluations are flagged low-confidence because they are a limited baseline, not a semantic assessment. For the dashboard, each assessed skill receives an evidence level per scored answer: no evidence = 0%, mention only = 30%, concrete example = 60%, or detailed explanation with actions/reasoning/outcome = 100%. The per-skill bar is the average evidence weight across scored questions that assessed the skill, including zero-evidence assessments. A one-question skill score is labeled **Low confidence coverage** and shown in a lighter color; two assessments are labeled **Building evidence**, and three or more **Repeated evidence**. Chart coverage is not overall proficiency or a hiring probability. The final summary includes the per-skill evidence bar chart and a strengths-versus-gaps radar chart. The candidate can download a PDF with scores, strengths, improvement areas, and feedback. Raw answer text and voice recordings are not included in the PDF.

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

## Groq configuration

Create a Groq API key in your Groq account. Copy `.env.example` to `.env` and replace its placeholder with your key. The `.env` file is excluded from Git:

```powershell
Copy-Item .env.example .env
```

Alternatively, set `$env:GROQ_API_KEY` in the terminal where you start the API. Environment variables already set in PowerShell take precedence over `.env`. The default model is `openai/gpt-oss-120b`, configured in `config.yaml`; override it with `$env:GROQ_MODEL`. The app loads `.env` at startup and does not write or log the key. Teammates need their own provider key. Never paste keys into source code, `config.yaml`, screenshots, or GitHub. If a key has been shared in chat or committed, revoke it and create a replacement.

To run without Groq, set `$env:INTERVIEW_AGENT_MODE = "local"` before starting the API. Local mode uses deterministic keyword matching and does not call an LLM.

## Build the Data Engineering RAG index

Install Ollama, then download the configured embedding model and build the local vector index from the Markdown files, including `rubrics.md`, `scoring_guide.md`, and `interview_qna.md`. Sections are chunked at configured character limits (with overlap), embedded in batches, and stored with role/skill/source metadata:

```powershell
ollama pull nomic-embed-text
python -m app.rag.build_index
```

Ollama must be running for indexing and for Data Engineer evaluations. Re-run the index command after changing rubric files. Each teammate builds their own `.chroma` index locally; the rubric Markdown files are shared through Git, but the vector database and API keys are not. RAG retrieval currently runs for job descriptions that identify a Data Engineer/Data Engineering role; other roles continue through the LLM without the Data Engineering rubrics.

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

The demo expects the API at `http://127.0.0.1:8000`. To use a different URL, set the `INTERVIEW_API_URL` environment variable before starting Streamlit. After generating questions, the candidate works through them sequentially with Previous/Next controls. Answers and per-question evaluations are kept for the current Streamlit session; the final question offers a summary once every question has been evaluated. When a candidate stops a browser recording, the app automatically sends it to the API for Groq Whisper transcription and places the transcript in the editable answer field. A retry action is available if transcription fails. Audio is sent to Groq and is not stored or logged by this app. Voice transcription is unavailable in local mode.
The UI allows up to 120 seconds for an API response by default because evaluation calls local embeddings and the LLM. Set `INTERVIEW_API_TIMEOUT_SECONDS` in the UI terminal to change that limit.
If you did not activate the virtual environment, replace `python` with `.\.venv\Scripts\python.exe` in the commands above.

## API quick reference

- `GET /health` — check that the API is running.
- `POST /interview/questions` — JSON body: `{"job_description": "...", "question_count": 5}`.
- `POST /interview/evaluate` — JSON body: `{"question": "...", "answer": "...", "required_skills": ["Python", "SQL"], "job_description": "..."}`.
- `POST /interview/transcribe` — raw audio request body (maximum 25 MB), with `Content-Type` set to its audio MIME type and optional `X-Audio-Filename`; available in Groq mode.

Question generation extracts recognized skills from the job description (cloud providers are grouped as one alternative skill). Pass those skills and the same job description when evaluating an answer; the UI does this automatically. The evaluation response includes `assessed_skills`, which are the supplied role skills actually relevant to that question; `matched_skills` and `missing_skills` classify only those assessed skills. It also includes `answer_relevant`, the evaluator's judgment about whether the answer substantively addressed the question. A response may be relevant and scored even when no role skill from the maintained catalog maps to that question. In Groq mode, the evaluator can recognize demonstrated evidence rather than requiring the candidate to repeat exact keywords.
Evaluation responses also include `confidence` (`high`, `medium`, or `low`). Local keyword-matching mode returns `low`; a low value asks for manual review rather than implying a reliable score.

## Tests

```powershell
python -m pytest
```

## Team ownership and contracts

Suggested independent work areas:

- **Question generation:** `app/agents/question_generator.py`. Keep `generate(job_description, question_count)` returning a list of question strings.
- **Answer evaluation:** `app/agents/answer_evaluator.py` and `app/utils/scoring.py`. Keep `evaluate(question, answer, required_skills, job_description=None)` returning `EvaluationDetails`.
- **Feedback:** `app/agents/feedback_writer.py` and `app/utils/formatting.py`. Keep `write(evaluation)` returning a string.
- **Integration/API:** `app/pipelines/interview_pipeline.py` and `app/main.py`.
- **Demo UI:** `ui/streamlit_app.py`.

Agree on contract changes with the integration owner before changing schemas. Create a feature branch per task, run `pytest` before opening a pull request, and avoid committing `.env` files or credentials.

## Configuration and screenshots

`config.yaml` contains non-secret defaults for the app and Groq agent settings. Never put API keys in it; credentials are read from environment variables.

There are no demo screenshots yet; add them here when a hosted or local demo is available.
