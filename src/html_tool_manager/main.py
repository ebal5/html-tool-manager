from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from html_tool_manager.api.tools import router as tools_router
from html_tool_manager.core.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle events."""
    # 起動時
    create_db_and_tables()
    yield
    # 終了時
    pass


app = FastAPI(lifespan=lifespan)


# セキュリティヘッダーのミドルウェア
@app.middleware("http")
async def add_security_headers(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Add security headers to all responses."""
    response = await call_next(request)

    # 共通セキュリティヘッダー
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # ツール用HTMLにはCSPを設定しない（iframe sandboxで保護）
    # 理由：ツールごとに使用するCDNが異なり、完全なリストを作成できないため
    if not request.url.path.startswith("/static/tools/"):
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

# Jinja2テンプレートの設定
templates = Jinja2Templates(directory="templates")

app.include_router(tools_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    """Render the tools list page (home page)."""
    return templates.TemplateResponse("index.html", {"request": request})


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
