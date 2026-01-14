"""
Gestion centralisée des sessions applicatives.

Responsabilités :
- gérer le cookie sid (signé)
- créer / restaurer une session Redis
- fournir ensure_session() utilisé par toutes les routes
"""

from __future__ import annotations

import secrets
import time
from typing import Optional, cast

from fastapi import HTTPException, Request, Response
from itsdangerous import BadSignature, URLSafeSerializer

from app.core.config import settings
from app.core.redis import delete_session, get_session, set_session


# -------------------------------------------------------------------
# Cookie signing
# -------------------------------------------------------------------

_sid_serializer = URLSafeSerializer(settings.app_secret_key, salt="sid")
state_serializer = URLSafeSerializer(settings.app_secret_key, salt="oauth-state")


def _new_session_id() -> str:
    return secrets.token_urlsafe(24)


def get_sid(request: Request) -> Optional[str]:
    raw = request.cookies.get("sid")
    if not raw:
        return None
    try:
        return cast(Optional[str], _sid_serializer.loads(raw))
    except BadSignature:
        return None


def set_sid_cookie(response: Response, sid: str) -> None:
    response.set_cookie(
        key="sid",
        value=_sid_serializer.dumps(sid),
        httponly=True,
        samesite=settings.cookie_samesite,  # ex: "lax"
        secure=settings.cookie_secure,      # True en prod https
        path="/",
        max_age=settings.session_max_age_seconds,  # ex: 8h
    )


def delete_sid_cookie(response: Response) -> None:
    response.delete_cookie("sid", path="/")


def ensure_session(request: Request, response: Response) -> str:
    """
    Garantit l'existence d'une session Redis valide ET du cookie sid côté client.
    Retourne toujours un sid valide.
    """
    sid = get_sid(request)

    if not sid:
        sid = _new_session_id()
        set_session(sid, {"created_at": time.time()})
        set_sid_cookie(response, sid)
        return sid

    # cookie présent => s'assurer que Redis existe
    session = get_session(sid)
    if not session:
        set_session(sid, {"created_at": time.time()})

    # Optionnel : refresh cookie (sliding expiration) si tu veux
    # set_sid_cookie(response, sid)

    return sid


def require_session(request: Request) -> str:
    sid = get_sid(request)
    if not sid:
        raise HTTPException(401, "Pas de session (cookie sid absent).")

    session = get_session(sid)
    if not session:
        raise HTTPException(401, "Session expirée ou introuvable.")

    return sid


def destroy_session(request: Request, response: Response) -> None:
    """
    Logout clean: supprime la session Redis + cookie.
    """
    sid = get_sid(request)
    if sid:
        delete_session(sid)
    delete_sid_cookie(response)
