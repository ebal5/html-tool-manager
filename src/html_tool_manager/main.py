from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from html_tool_manager.core.db import create_db_and_tables
from html_tool_manager.api.tools import router as tools_router

app = FastAPI()

# 静的ファイルの提供
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2Templatesの設定
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(tools_router, prefix="/api") # APIのパスを/api以下に移動

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/tools/create", response_class=HTMLResponse)
async def create_tool_page(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.get("/tools/edit/{tool_id}", response_class=HTMLResponse)
async def edit_tool_page(request: Request, tool_id: int):
    return templates.TemplateResponse("edit.html", {"request": request, "tool_id": tool_id})

@app.get("/tools/view/{tool_id}", response_class=HTMLResponse)
async def view_tool_page(request: Request, tool_id: int):
    # TODO: tool_id からツール情報を取得し、そのツールのHTMLを表示するロジック
    #       現時点では仮の表示
    return templates.TemplateResponse("tool_viewer.html", {"request": request, "tool_id": tool_id})
