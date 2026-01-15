from typing import Any, Dict, List, Optional, AsyncIterator

import json

from fastapi import APIRouter, HTTPException, Request, Response, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ai_app.clients.llm import LLMClient
from ai_app.core.auth import verify_ai_token

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(verify_ai_token)])
llm = LLMClient()


class SummarizeJqlBody(BaseModel):
    jql: str | None = Field(default=None, min_length=1, max_length=2000)
    max_results: int = Field(default=20, ge=1, le=50)
    cloud_id: Optional[str] = None
    issues: Optional[list] = None  # optional pre-fetched issues payload


class AnalyzeIssueBody(BaseModel):
    issue_key: str = Field(min_length=1, max_length=50)
    cloud_id: Optional[str] = None
    max_links: int = Field(default=2, ge=1, le=12)
    max_comments: int = Field(default=2, ge=1, le=30)


def _sse(event: str, data: Dict[str, Any] | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/summarize-jql")
async def summarize_jql(body: SummarizeJqlBody) -> Dict[str, Any]:
    # Accept optional pre-fetched issues; otherwise use a canned example.
    issues = body.issues
    if not issues:
        issues = [
            {"key": "PROJ-1", "summary": "Exemple", "status": "Open"},
        ][: body.max_results]

    # simple canned response (placeholder for real LLM call)
    result = {"summary": "Résumé exemple", "highlights": [], "risks": [], "next_actions": []}

    return {"cloud_id": body.cloud_id or "demo", "count": len(issues), "result": result}


@router.post("/analyze-issue")
async def analyze_issue(body: AnalyzeIssueBody) -> Dict[str, Any]:
    # This endpoint accepts the issue key OR a pre-built payload (issue/comments/dependencies).
    if body.issue_key is None:
        # expect a full payload provided in request.json (handled by the proxy)
        raise HTTPException(400, "issue_key or payload expected")

    # canned analysis
    return {"cloud_id": body.cloud_id or "demo", "result": "Analyse exemple"}


@router.post("/analyze-issue/stream")
async def analyze_issue_stream(body: AnalyzeIssueBody) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        yield _sse("log", "Début de l'analyse")
        yield _sse("log", "Synthèse...")
        yield _sse("result", {"text": "Analyse progressive - résultat exemple"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
