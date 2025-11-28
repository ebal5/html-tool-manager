from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from html_tool_manager.api.tools import router as tools_router
from html_tool_manager.core.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクルイベントを管理します。"""
    # 起動時
    create_db_and_tables()
    yield
    # 終了時
    pass


app = FastAPI(lifespan=lifespan)

# 静的ファイルの提供
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2テンプレートの設定
templates = Jinja2Templates(directory="templates")

app.include_router(tools_router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    """ツール一覧ページ（ホームページ）をレンダリングします。"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/tools/create", response_class=HTMLResponse)
async def create_tool_page(request: Request) -> HTMLResponse:
    """ツール作成ページをレンダリングします。"""
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/tools/edit/{tool_id}", response_class=HTMLResponse)
async def edit_tool_page(request: Request, tool_id: int) -> HTMLResponse:
    """ツール編集ページをレンダリングします。"""
    return templates.TemplateResponse("edit.html", {"request": request, "tool_id": tool_id})


@app.get("/tools/view/{tool_id}", response_class=HTMLResponse)
async def view_tool_page(request: Request, tool_id: int) -> HTMLResponse:
    """ツール表示ページをレンダリングします。"""
    return templates.TemplateResponse("tool_viewer.html", {"request": request, "tool_id": tool_id})
