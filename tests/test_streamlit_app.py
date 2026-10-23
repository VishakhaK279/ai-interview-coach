from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return self.payload


def test_interview_navigation_preserves_results_and_shows_summary() -> None:
    evaluation_payloads = {
        "Tell me about Python.": {
            "score": 80,
            "confidence": "high",
            "feedback": "Python feedback.",
            "assessed_skills": ["Python"],
            "skill_evidence": [{"skill": "Python", "level": "example"}],
            "content_safe": True,
            "sources": [],
            "request_id": "request-python",
        },
        "Tell me about SQL.": {
            "score": 60,
            "confidence": "low",
            "feedback": "SQL feedback.",
            "assessed_skills": ["SQL"],
            "skill_evidence": [{"skill": "SQL", "level": "mention"}],
            "content_safe": True,
            "sources": [],
            "request_id": "request-sql",
        },
    }
    submitted_answers: dict[str, str] = {}

    def fake_post(url: str, json: dict, timeout: int) -> FakeResponse:
        if url.endswith("/interview/questions"):
            return FakeResponse(
                {
                    "questions": ["Tell me about Python.", "Tell me about SQL."],
                    "skills": ["Python", "SQL"],
                }
            )
        question = json["question"]
        submitted_answers[question] = json["answer"]
        return FakeResponse(evaluation_payloads[question])

    with patch("requests.post", side_effect=fake_post):
        app = AppTest.from_file(
            Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py",
            default_timeout=10,
        ).run()
        app.text_area[0].set_value("Python and SQL role").run()
        app.button[0].click().run()

        app.text_area[1].set_value("I used Python to clean the data.").run()
        next(button for button in app.button if button.label == "Evaluate answer").click().run()
        next(button for button in app.button if button.label == "Next question").click().run()

        assert app.subheader[0].value == "Question 2 of 2"
        app.text_area[1].set_value("I wrote a SQL join.").run()
        next(button for button in app.button if button.label == "Evaluate answer").click().run()
        next(
            button
            for button in app.button
            if button.label == "Finish and view summary"
        ).click().run()

        assert not app.exception
        assert any(header.value == "Interview summary" for header in app.header)
        assert [metric.value for metric in app.metric] == ["70/100"]
        assert submitted_answers == {
            "Tell me about Python.": "I used Python to clean the data.",
            "Tell me about SQL.": "I wrote a SQL join.",
        }
        summary_markdown = [element.value for element in app.markdown]
        assert "**Question 1:** 80/100" in summary_markdown
        assert "**Question 2:** 60/100" in summary_markdown
        assert "Low confidence — manual review needed." in [
            warning.value for warning in app.warning
        ]
        assert len(app.get("plotly_chart")) == 1
        assert any(
            "not a measure of your overall skill" in item.value
            for item in app.info
        )
        assert any(
            "Answers with examples or detailed evidence" in item.value
            for item in app.markdown
        )
        assert any(
            "Answers that could use more detail" in item.value
            for item in app.markdown
        )
        assert any(
            "not a hiring recommendation" in item.value
            for item in app.markdown
        )
        assert any(
            button.label == "Download candidate report (PDF)"
            for button in app.get("download_button")
        )


def test_summary_dashboard_accepts_legacy_integer_skill_scores() -> None:
    with patch(
        "app.utils.summary.skill_evidence_scores",
        return_value={"Python": 30},
    ):
        app = AppTest.from_file(
            Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py",
            default_timeout=10,
        ).run()
        app.session_state["questions"] = ["Tell me about Python."]
        app.session_state["skills"] = ["Python"]
        app.session_state["evaluation_results"] = {
            0: {
                "score": 30,
                "feedback": "Mention-level evidence.",
                "assessed_skills": ["Python"],
                "skill_evidence": [{"skill": "Python", "level": "mention"}],
            }
        }
        app.session_state["show_summary"] = True
        app.run()

    assert not app.exception
    assert any(header.value == "Skill evidence dashboard" for header in app.subheader)
    assert len(app.get("plotly_chart")) == 1
    assert "Low confidence coverage (legacy score)" in str(app.dataframe[0].value)


def test_recording_is_transcribed_automatically_once() -> None:
    class FakeAudioRecording:
        type = "audio/webm"
        name = "answer.webm"

        def getvalue(self) -> bytes:
            return b"recorded audio"

    requests_made: list[str] = []
    audio_widget_keys: list[str] = []

    def fake_post(url: str, **kwargs) -> FakeResponse:
        requests_made.append(url)
        if url.endswith("/interview/questions"):
            return FakeResponse(
                {
                    "questions": [
                        "Tell me about a Python project.",
                        "Tell me about a SQL project.",
                    ],
                    "skills": ["Python"],
                }
            )
        if url.endswith("/interview/transcribe"):
            assert kwargs["data"] == b"recorded audio"
            assert kwargs["headers"]["Content-Type"] == "audio/webm"
            return FakeResponse({"text": "I built a Python data pipeline."})
        raise AssertionError(f"Unexpected API request: {url}")

    def fake_audio_input(label: str, key: str):
        audio_widget_keys.append(key)
        return FakeAudioRecording() if key.endswith("_0") else None

    with (
        patch("requests.post", side_effect=fake_post),
        patch("streamlit.audio_input", side_effect=fake_audio_input),
    ):
        app = AppTest.from_file(
            Path(__file__).resolve().parents[1] / "ui" / "streamlit_app.py",
            default_timeout=10,
        ).run()
        app.text_area[0].set_value("Python role").run()
        app.button[0].click().run()

        assert not app.exception
        assert app.text_area[1].value == "I built a Python data pipeline."
        assert any("Transcription complete" in item.value for item in app.success)
        assert not any(button.label == "Transcribe recording" for button in app.button)
        assert requests_made.count("http://127.0.0.1:8000/interview/transcribe") == 1

        next(button for button in app.button if button.label == "Next question").click().run()

        assert app.subheader[0].value == "Question 2 of 2"
        assert app.text_area[1].value == ""
        assert not app.success
        assert len(set(audio_widget_keys)) == 2
        assert requests_made.count("http://127.0.0.1:8000/interview/transcribe") == 1
