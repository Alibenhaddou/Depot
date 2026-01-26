from fastapi import Header, HTTPException
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from ai_app.core.config import settings


def verify_ai_token(authorization: str | None = Header(default=None)) -> dict:
    # If disabled, accept calls without auth (dev / local).
    if not settings.ai_auth_enabled:
        return {}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Token manquant")

    token = authorization.split(" ", 1)[1]
    # Token is signed by the main API and validated here.
    serializer = URLSafeTimedSerializer(
        settings.ai_shared_secret, salt="ai-service-token"
    )
    try:
        return serializer.loads(token, max_age=settings.ai_token_ttl_seconds)
    except SignatureExpired:
        raise HTTPException(401, "Token expiré")
    except BadSignature:
        raise HTTPException(401, "Token invalide")
