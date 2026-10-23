# AI Interview Coach

AI Interview Coach is a practice application that turns a job description into
role-focused interview questions, evaluates answers, and provides actionable
feedback. Candidates can type or speak their answers, review results question by
question, and download a PDF summary.

This is a coaching tool. Its scores are generated automatically and should not be
treated as a hiring decision or a definitive measure of a candidate's ability.

## What the application does

1. Accepts a pasted or uploaded job description.
2. Extracts recognized role skills and generates interview questions.
3. Lets the candidate answer each question by text or voice.
4. Evaluates each answer against its question and relevant role criteria.
5. Shows feedback, confidence, and evidence coverage in a final summary.
6. Offers a PDF report containing scores and coaching feedback.

The Streamlit interface calls a FastAPI backend. In the default `groq` mode,
Groq's language model generates questions, evaluates answers, and writes feedback.
Local mode provides a deterministic keyword-matching baseline; it is not a
semantic substitute for Groq evaluation.

## How answer evaluation works

The evaluator focuses on whether an answer responds to the specific question and
what relevant evidence it contains. It is instructed not to reward verbosity or
penalize concise answers, grammar, accent, or writing style. A short answer can
score well when it gives a clear, relevant example; a long answer does not earn
credit merely for being long.

When operating in Groq mode, the response includes:

- A question-level score from 0 to 100 and written feedback.
- Skills assessed for that particular question, with matched and missing skills.
- Evidence levels for assessed skills: `none` (0%), `mention` (30%), `example`
  (60%), or `detailed` (100%).
- Confidence (`high`, `medium`, or `low`) and an answer-relevance decision.

The dashboard's per-skill percentage is the average evidence level across scored
answers that assessed that skill. It is evidence shown in those answers, not
overall skill proficiency. When a result has low confidence, the interface asks
for manual review. Answers deemed irrelevant or blocked by the content-safety
guardrail are not scored.

## How RAG is used

For Data Engineer/Data Engineering job descriptions, the application retrieves
relevant passages from the local Data Engineering rubrics and scoring guide. It
uses Ollama to embed the search query and Chroma to find the most relevant
passages. The query includes the job description, role skills, interview question,
and candidate answer. Retrieved passages are provided to the Groq evaluator and
feedback writer as reference context.

The reference documents are in `data/rubrics/data_engineering/`. Their Markdown
content is source material; the generated Chroma index is stored locally in
`.chroma/`. Other roles do not currently use the Data Engineering rubric index.
RAG adds relevant guidance to the model's context; it does not independently
verify a candidate's claims.

## Main features

- **Question generation:** creates questions from the supplied job description.
- **Answer evaluation:** provides a score, skill evidence, and specific feedback.
- **Sequential interview flow:** supports Previous/Next navigation and a final
  summary after all questions have been evaluated.
- **Voice answers:** records audio in the browser, sends it for Groq transcription,
  and places the transcript in an editable answer field. Audio is not stored or
  logged by this application.
- **Skill evidence dashboard:** displays a horizontal per-skill evidence chart,
  the number of assessed questions, and a plain-language summary of evidence
  versus areas where answers could use more detail.
- **Candidate PDF:** exports scores, strengths, improvement areas, and feedback.
  Raw answers and audio are not included.
- **Audit logging:** records evaluation metadata with a request ID to the console
  and `logs/app.log`; candidate answer text and raw job descriptions are not
  included in those audit events.

## Requirements

- Python 3.10 or newer.
- A Groq API key for question generation, semantic evaluation, feedback, and
  transcription.
- For Data Engineering RAG: Ollama running locally with the configured embedding
  model, `nomic-embed-text`.

## Setup

Run these commands from the project directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If virtual-environment activation is unavailable, use the environment's Python
executable directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Configure Groq

Copy `.env.example` to `.env` and add your Groq API key:

```powershell
Copy-Item .env.example .env
```

Alternatively, set the key in the terminal where the API is started:

```powershell
$env:GROQ_API_KEY = "your-api-key"
```

Never commit `.env` or put API keys in `config.yaml`. The default model and
non-secret application settings are configured in `config.yaml`.

## Build the Data Engineering RAG index

Install and start Ollama, then download the configured embedding model and build
the local vector index:

```powershell
ollama pull nomic-embed-text
python -m app.rag.build_index
```

Rebuild the index after changing files under
`data/rubrics/data_engineering/`. Ollama must be available when indexing and when
evaluating Data Engineering answers with RAG enabled.

## Run the application

Start the API in one terminal:

```powershell
python -m uvicorn app.main:app --reload
```

Check API health at <http://127.0.0.1:8000/health> or open the interactive API
documentation at <http://127.0.0.1:8000/docs>.

Start the Streamlit interface in another terminal:

```powershell
python -m streamlit run ui/streamlit_app.py
```

By default, the interface connects to `http://127.0.0.1:8000`. Set
`INTERVIEW_API_URL` in the Streamlit terminal to use a different API address.
The UI request timeout defaults to 120 seconds and can be changed with
`INTERVIEW_API_TIMEOUT_SECONDS`.

### Local keyword mode

To run the backend without Groq, set this before starting the API:

```powershell
$env:INTERVIEW_AGENT_MODE = "local"
python -m uvicorn app.main:app --reload
```

Local mode uses deterministic keyword matching, has limited relevance assessment,
and does not provide reliable content-safety moderation. Voice transcription
requires Groq mode.

## API endpoints

- `GET /health` — reports whether the API is running.
- `POST /interview/questions` — generates questions from a job description.
- `POST /interview/evaluate` — evaluates one answer for one question.
- `POST /interview/transcribe` — transcribes audio in Groq mode; request body is
  raw audio and is limited to 25 MB.

## Logs and privacy

Evaluation audit records include the request ID, outcome, score, assessed skills,
retrieved source paths, and a fingerprint of the job description. They do not
include the raw candidate answer or full job description. The fingerprint is a
correlation value, not anonymization. Logs are written under `logs/` and rotated
by the application.

Voice recordings are sent to Groq for transcription and are not stored or logged
by this application. Review your provider's data handling terms before using
real candidate information.

## Run tests

```powershell
python -m pytest
```
