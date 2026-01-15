from pathlib import Path


def test_ai_service_openapi_contains_ai_paths():
    spec_path = Path(__file__).resolve().parents[1] / "services" / "ai_service" / "openapi.yaml"
    text = spec_path.read_text(encoding="utf-8")
    assert "/ai/summarize-jql" in text
    assert "/ai/analyze-issue" in text
    assert "/ai/analyze-issue/stream" in text
