import json
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import Settings
from app.models import AnalysisResponse, Incident
from app.service import InvestigationService, ServiceUnavailable

logger = logging.getLogger("opspilot")


def create_app(settings: Settings | None = None):
    settings = settings or Settings()
    service = InvestigationService(settings)

    @asynccontextmanager
    async def lifespan(_app):
        try:
            await service.initialize()
            yield
        finally:
            await service.close()

    app = FastAPI(
        title="OpsPilot",
        version="0.1.0",
        lifespan=lifespan,
        description="Read-only incident investigation. Demo mode is not an LLM.",
    )
    app.state.service = service
    app.mount("/static", StaticFiles(directory=settings.static), name="static")

    async def authorize(authorization: str | None = Header(default=None)):
        expected = "Bearer " + settings.api_token
        if settings.api_token and not secrets.compare_digest(authorization or "", expected):
            raise HTTPException(401, "A valid OpsPilot API token is required")

    @app.middleware("http")
    async def limits_and_headers(request: Request, call_next):
        # Enforce the actual streamed body limit, including chunked requests.
        if request.method == "POST":
            body = bytearray()
            async for part in request.stream():
                body.extend(part)
                if len(body) > 65536:
                    return Response("Request body exceeds 64 KiB", status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        )
        if request.url.path == "/docs":
            # FastAPI's Swagger page uses a CDN and inline initialization; the
            # incident interface keeps its stricter policy and no external assets.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data: https://fastapi.tiangolo.com; frame-ancestors 'none'"
            )
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/", include_in_schema=False)
    async def home():
        return FileResponse(settings.static / "index.html")

    @app.get("/healthz")
    async def health():
        return {"status": "ok"}

    @app.get("/readyz")
    async def ready():
        if not service.ready:
            raise HTTPException(503, "Index is not ready")
        return {"status": "ready", "mode": settings.mode}

    @app.get("/api/config")
    async def config():
        return {
            "mode": settings.mode,
            "auth_required": bool(settings.api_token),
            "runbooks": len({c.runbook for c in service.chunks}),
            "chunks": len(service.chunks),
        }

    @app.get("/api/examples", dependencies=[Depends(authorize)])
    async def examples():
        fixtures = json.loads(settings.fixtures.read_text(encoding="utf-8"))
        return [{"id": f["id"], "incident": f["incident"]} for f in fixtures]

    @app.post("/api/analyze", response_model=AnalysisResponse, dependencies=[Depends(authorize)])
    async def analyze(incident: Incident):
        try:
            result = await service.analyze(incident)
            # No raw incident, provider exception text, or credentials in application logs.
            logger.info(
                "investigation_completed request_id=%s mode=%s latency_ms=%s",
                result.request_id,
                result.mode,
                result.latency_ms,
            )
            return result
        except ServiceUnavailable as error:
            raise HTTPException(503, str(error)) from None
        except Exception as error:
            logger.warning("investigation_failed error_type=%s", type(error).__name__)
            raise HTTPException(
                502, "Investigation failed: check provider availability and model configuration"
            ) from None

    @app.get("/metrics", dependencies=[Depends(authorize)])
    async def metrics():
        return Response(generate_latest(service.registry), media_type=CONTENT_TYPE_LATEST)

    return app


app = create_app()
