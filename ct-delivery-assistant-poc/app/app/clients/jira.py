from __future__ import annotations
from fastapi import HTTPException, Request
from typing import Any, Dict, Optional, cast

import httpx


class JiraClient:
    """Thin async client for the Atlassian Jira Cloud REST API (ex/jira).

    The implementation is intentionally small: it provides a thin wrapper
    around httpx.AsyncClient and normalizes HTTP error handling into
    application-level exceptions used by the routes.
    """
    def __init__(self, access_token: str, cloud_id: str, timeout: int = 30):
        self.access_token = access_token
        self.cloud_id = cloud_id
        self._client = httpx.AsyncClient(timeout=timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
        }

    @property
    def _ex_base_url(self) -> str:
        return f"https://api.atlassian.com/ex/jira/{self.cloud_id}/rest/api/3"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform an HTTP request to the Jira Ex API and normalize errors.

        Returns parsed JSON on success. Raises PermissionError on 401 or
        propagates an httpx.HTTPStatusError with a short snippet for other
        HTTP error responses.
        """
        url = f"{self._ex_base_url}{path}"

        r = await self._client.request(
            method=method,
            url=url,
            headers=self._headers,
            params=params,
            json=json_body,
        )

        if r.status_code == 401:
            raise PermissionError("Token Jira refusé ou expiré")

        if r.status_code >= 400:
            snippet = (r.text or "")[:300]
            snippet = snippet.replace("\n", " ")
            raise httpx.HTTPStatusError(
                message=f"Jira error {r.status_code}: {snippet}",
                request=r.request,
                response=r,
            )

        return r.json()

    async def get_issue(
        self,
        issue_key: str,
        *,
        expand: Optional[str] = None,
    ) -> Any:
        params: Optional[Dict[str, Any]] = None
        if expand:
            params = {"expand": expand}
        return await self._request(
            "GET",
            f"/issue/{issue_key}",
            params=params,
        )

    async def get_issue_comments(
        self,
        issue_key: str,
        max_results: int = 20,
    ) -> Any:
        max_results = max(1, min(max_results, 50))
        return await self._request(
            "GET",
            f"/issue/{issue_key}/comment",
            params={"maxResults": max_results},
        )

    async def search_jql(
        self,
        jql: str,
        max_results: int = 20,
        next_page_token: Optional[str] = None,
    ) -> Any:
        max_results = max(1, min(max_results, 50))
        body: Dict[str, Any] = {
            "jql": jql,
            "maxResults": max_results,
            "fields": [
                "summary",
                "status",
                "issuetype",
                "project",
                "assignee",
                "updated",
                "created",
            ],
            "fieldsByKeys": True,
        }
        if next_page_token:
            body["nextPageToken"] = next_page_token
        try:
            return await self._request("POST", "/search/jql", json_body=body)
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code in (404, 410):
                return await self._request("POST", "/search", json_body=body)
            raise


from typing import Dict

def select_cloud_id(session: Dict[str, Any], request: Request) -> str:
    """
    Détermine quelle instance Jira utiliser pour la requête courante.

    Priorité :
    1) ?cloud_id=... dans l'URL (override explicite)
    2) session["active_cloud_id"]
    3) premier cloudId connecté

    Robustesse :
    - si cloud_ids est vide mais tokens_by_cloud existe, on dérive cloud_ids
    """
    tbc = session.get("tokens_by_cloud") or {}
    cloud_ids: list[str] = cast(list[str], session.get("cloud_ids") or list(tbc.keys()))

    requested: Optional[str] = cast(Optional[str], request.query_params.get("cloud_id"))
    if requested:
        if requested not in cloud_ids:
            raise HTTPException(400, "cloud_id inconnu ou non connecté")
        return requested

    active: Optional[str] = cast(Optional[str], session.get("active_cloud_id"))
    if active and active in cloud_ids:
        return active

    if cloud_ids:
        return cloud_ids[0]

    raise HTTPException(400, "Aucune instance Jira connectée")
