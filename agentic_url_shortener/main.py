from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from .config import Settings
from .database import Database
from .schemas import (
    AnalyticsResponse,
    ApprovalRequest,
    CreateRunRequest,
    CreateUrlRequest,
    ResumeRequest,
    UrlResponse,
)
from .url_service import ShortUrl, UrlError, UrlService
from .workflow import WorkflowService, WorkflowStateError


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    database = Database(config.database_path)
    service = UrlService(database)
    workflow: WorkflowService | None = None

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        nonlocal workflow
        database.initialize()
        config.workspace_root.mkdir(parents=True, exist_ok=True)
        workflow = WorkflowService(config, database)
        app.state.workflow = workflow
        yield

    app = FastAPI(title="Agentic URL Shortener", version="0.1.0", lifespan=lifespan)
    app.state.settings = config
    app.state.database = database
    app.state.url_service = service

    @app.exception_handler(UrlError)
    async def url_error(_: Request, error: UrlError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"error": {"code": error.code, "message": str(error)}},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": error.errors()}},
        )

    @app.exception_handler(KeyError)
    async def not_found(_: Request, error: KeyError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"error": {"code": "RUN_NOT_FOUND", "message": str(error)}},
        )

    @app.exception_handler(WorkflowStateError)
    async def invalid_run_state(_: Request, error: WorkflowStateError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"error": {"code": "INVALID_RUN_STATE", "message": str(error)}},
        )

    @app.exception_handler(ValueError)
    async def bad_request(_: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "BAD_REQUEST", "message": str(error)}},
        )

    def workflows() -> WorkflowService:
        if workflow is None:
            raise RuntimeError("Application has not started")
        return workflow

    def response(item: ShortUrl, request: Request) -> UrlResponse:
        return UrlResponse(
            shortCode=item.short_code, originalUrl=item.original_url,
            shortUrl=f"{str(request.base_url).rstrip('/')}/{item.short_code}",
            createdAt=item.created_at, expiresAt=item.expires_at,
            redirectCount=item.redirect_count, lastAccessedAt=item.last_accessed_at,
            isActive=item.is_active,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @app.post("/api/v1/urls", response_model=UrlResponse, status_code=201)
    def create_url(payload: CreateUrlRequest, request: Request) -> UrlResponse:
        return response(service.create(str(payload.url), payload.custom_alias, payload.expires_at), request)

    @app.get("/api/v1/urls/{short_code}", response_model=UrlResponse)
    def get_url(short_code: str, request: Request) -> UrlResponse:
        return response(service.get(short_code), request)

    @app.delete("/api/v1/urls/{short_code}", status_code=204)
    def delete_url(short_code: str) -> Response:
        service.delete(short_code)
        return Response(status_code=204)

    @app.get("/api/v1/urls/{short_code}/analytics", response_model=AnalyticsResponse)
    def analytics(short_code: str) -> AnalyticsResponse:
        item = service.get(short_code)
        return AnalyticsResponse(shortCode=item.short_code, redirectCount=item.redirect_count,
            lastAccessedAt=item.last_accessed_at, createdAt=item.created_at, expiresAt=item.expires_at)

    @app.post("/api/v1/runs", status_code=201)
    def create_run(payload: CreateRunRequest) -> dict:
        return workflows().start(payload.requirement, payload.scenario)  # type: ignore[arg-type]

    @app.get("/api/v1/runs/{run_id}")
    def get_run(run_id: str) -> dict:
        return workflows().get(run_id)

    @app.get("/api/v1/runs/{run_id}/events")
    def get_events(run_id: str) -> dict:
        return {"data": workflows().events(run_id)}

    @app.post("/api/v1/runs/{run_id}/approvals")
    def approve_run(run_id: str, payload: ApprovalRequest) -> dict:
        return workflows().approve(run_id, payload.action, payload.approved, payload.actor)

    @app.post("/api/v1/runs/{run_id}/resume")
    def resume_run(run_id: str, payload: ResumeRequest) -> dict:
        return workflows().resume(run_id, payload.clarification)

    @app.post("/api/v1/runs/{run_id}/cancel")
    def cancel_run(run_id: str) -> dict:
        return workflows().cancel(run_id)

    @app.get("/api/v1/metrics")
    def metrics() -> dict:
        return workflows().metrics()

    @app.get("/{short_code}", include_in_schema=False)
    def redirect(short_code: str) -> RedirectResponse:
        return RedirectResponse(service.resolve(short_code).original_url, status_code=307)

    return app


app = create_app()
