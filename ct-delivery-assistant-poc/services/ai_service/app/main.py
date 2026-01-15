from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.responses import StreamingResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.routes.ai import router as ai_router

app = FastAPI(title="AI Service (scaffold)", version="0.1.0")

# Health endpoints
@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"

@app.get("/ready", response_class=PlainTextResponse)
async def ready():
    return "ready"

# Metrics (Prometheus)
@app.get("/metrics")
async def metrics():
    data = generate_latest()
    return StreamingResponse(iter([data]), media_type=CONTENT_TYPE_LATEST)

# Include AI routes
app.include_router(ai_router)
