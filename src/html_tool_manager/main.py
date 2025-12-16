import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from apscheduler.schedulers.background import BackgroundScheduler  # type: ignore[import-untyped]
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import text
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from html_tool_manager.api.backup import router as backup_router
from html_tool_manager.api.snapshots import router as snapshots_router
from html_tool_manager.api.templates import router as templates_router
from html_tool_manager.api.tools import router as tools_router
from html_tool_manager.core.backup import BackupService
from html_tool_manager.core.config import app_settings, backup_settings
from html_tool_manager.core.db import DATABASE_URL, create_db_and_tables, engine

logger = logging.getLogger(__name__)


def _get_db_path_from_url(url: str) -> Path:
    """Extract database file path from SQLite URL.

    Args:
        url: SQLite database URL (e.g., "sqlite:///./tools.db").

    Returns:
        Path object pointing to the database file.

    Raises:
        ValueError: If URL scheme is not sqlite or database is in-memory.

    """
    parsed = urlparse(url)
    if parsed.scheme != "sqlite":
        raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

    # Handle SQLite URL path (remove leading '/' for relative paths)
    db_path = parsed.path
    if db_path.startswith("///"):
        # Absolute path: sqlite:////absolute/path/db.db
        db_path = db_path[3:]
    elif db_path.startswith("/./"):
        # Relative path: sqlite:///./relative/path/db.db
        db_path = db_path[3:]
    elif db_path.startswith("/"):
        # Simple relative path: sqlite:///db.db
        db_path = db_path[1:]

    if not db_path or db_path == ":memory:":
        raise ValueError("Cannot backup in-memory database")

    return Path(db_path)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle events."""
    # 起動時: DB初期化
    create_db_and_tables()

    # バックアップサービス初期化
    db_path = _get_db_path_from_url(DATABASE_URL)
    backup_service = BackupService(
        db_path=str(db_path),
        backup_dir=backup_settings.backup_dir,
        max_generations=backup_settings.backup_max_generations,
    )
    app.state.backup_service = backup_service

    # 起動時バックアップ
    if backup_settings.backup_on_startup:
        try:
            backup_service.create_backup()
            logger.info("Startup backup created successfully")
        except Exception as e:
            logger.error("Failed to create startup backup: %s", e)

    # スケジューラ起動（app.stateに格納）
    app.state.scheduler = BackgroundScheduler()
    app.state.scheduler.add_job(
        backup_service.create_backup,
        "interval",
        hours=backup_settings.backup_interval_hours,
        id="scheduled_backup",
        max_instances=1,  # 同時実行を防止
        coalesce=True,  # 複数のジョブをまとめて実行
    )
    app.state.scheduler.start()
    logger.info("Backup scheduler started (interval: %d hours)", backup_settings.backup_interval_hours)

    yield

    # 終了時: スケジューラ停止（実行中のジョブ完了を待機）
    if hasattr(app.state, "scheduler") and app.state.scheduler.running:
        app.state.scheduler.shutdown(wait=True)
        logger.info("Backup scheduler stopped")


app = FastAPI(lifespan=lifespan)


# セキュリティヘッダーのミドルウェア
@app.middleware("http")
async def add_security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Add security headers to all responses."""
    response = await call_next(request)

    # 共通セキュリティヘッダー
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"  # クリックジャッキング対策
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # ツール用HTMLにはCSPを設定しない（iframe sandboxで保護）
    # 理由：ツールごとに使用するCDNが異なり、完全なリストを作成できないため
    if not request.url.path.startswith("/tools/"):
        # アプリケーション本体には完全なCSP
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com https://cdn.jsdelivr.net "
            "https://cdn.tailwindcss.com 'unsafe-inline' 'unsafe-eval';"
            "style-src 'self' https://cdn.jsdelivr.net https://cdn.tailwindcss.com 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' https://cdn.jsdelivr.net; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none'; "
            "base-uri 'self';"
        )

    return response


# 静的ファイルの提供
app.mount("/static", StaticFiles(directory="static"), name="static")
# ツールファイルの提供（環境変数で設定可能なディレクトリ）
# ディレクトリが存在しない場合は作成（CI環境やクリーンインストール対応）
tools_dir = Path(app_settings.tools_dir)
tools_dir.mkdir(parents=True, exist_ok=True)
app.mount("/tools", StaticFiles(directory=str(tools_dir)), name="tools")

# Jinja2テンプレートの設定
templates = Jinja2Templates(directory="templates")

app.include_router(tools_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(snapshots_router, prefix="/api")
app.include_router(templates_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    """Render the tools list page (home page)."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/templates", response_class=HTMLResponse)
async def templates_page(request: Request) -> HTMLResponse:
    """Render the templates gallery page."""
    return templates.TemplateResponse("templates.html", {"request": request})


@app.get("/tools/create", response_class=HTMLResponse)
async def create_tool_page(request: Request) -> HTMLResponse:
    """Render the tool creation page."""
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/tools/edit/{tool_id}", response_class=HTMLResponse)
async def edit_tool_page(request: Request, tool_id: int) -> HTMLResponse:
    """Render the tool edit page."""
    return templates.TemplateResponse("edit.html", {"request": request, "tool_id": tool_id})


@app.get("/tools/view/{tool_id}", response_class=HTMLResponse)
async def view_tool_page(request: Request, tool_id: int) -> HTMLResponse:
    """Render the tool viewer page."""
    return templates.TemplateResponse("tool_viewer.html", {"request": request, "tool_id": tool_id})


@app.get("/backup", response_class=HTMLResponse)
async def backup_page(request: Request) -> HTMLResponse:
    """Render the backup management page."""
    return templates.TemplateResponse("backup.html", {"request": request})


@app.get("/health", response_class=JSONResponse)
async def health_check() -> JSONResponse:
    """Health check endpoint for monitoring and container orchestration.

    Returns:
        JSON response with health status and component checks.

    """
    health_status: dict[str, Any] = {
        "status": "healthy",
        "components": {
            "database": "unknown",
        },
    }

    # Database health check
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except SQLAlchemyError as e:
        logger.error("Database health check failed: %s", e, exc_info=True)
        health_status["status"] = "unhealthy"
        health_status["components"]["database"] = "unhealthy"

    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)
