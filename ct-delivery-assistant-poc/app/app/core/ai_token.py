from itsdangerous import URLSafeTimedSerializer

from app.core.config import settings


def generate_ai_token(payload: dict) -> str:
    serializer = URLSafeTimedSerializer(settings.ai_shared_secret, salt="ai-service-token")
    return serializer.dumps(payload)
