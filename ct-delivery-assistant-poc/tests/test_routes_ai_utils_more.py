import types

from app.routes import ai as ai_mod


def test_iter_text_nodes_and_adf_variants():
    adf = {"a": {"b": [{"text": "x"}, {"text": ""}], "c": "y"}}
    parts = list(ai_mod._iter_text_nodes(adf))
    assert "x" in parts

    assert ai_mod._adf_to_text("str", fallback="f") == "str"


def test_extract_links_inward_and_filter():
    fields = {"issuelinks": [{"type": {"name": "t"}, "inwardIssue": {"key": "I"}}, {"type": {}, "outwardIssue": {}}]}
    links = ai_mod._extract_links(fields, limit=5)
    assert any(l.get("key") == "I" for l in links)


def test_sse_with_string_payload():
    s = ai_mod._sse("log", "plain text")
    assert "plain text" in s


def test__llm_step_generic_exception(monkeypatch):
    class FakeLLM:
        async def chat_text(self, *a, **k):
            raise Exception("oops")

    try:
        # call through and expect HTTPException
        import asyncio
        asyncio.run(ai_mod._llm_step(FakeLLM(), title="T", system="s", user="u"))
        assert False, "expected"
    except Exception as e:
        # should be HTTPException with status_code 502
        assert hasattr(e, "status_code") and getattr(e, "status_code") == 502
