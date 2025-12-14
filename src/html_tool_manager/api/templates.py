"""Template library API endpoints."""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from html_tool_manager.core.db import get_session
from html_tool_manager.models import ToolCreate, ToolRead
from html_tool_manager.models.tool import NAME_MAX_LENGTH
from html_tool_manager.repositories import ToolRepository

router = APIRouter(prefix="/templates", tags=["templates"])

# テンプレートディレクトリの設定
TEMPLATES_DIR = Path("static/templates")
TEMPLATES_JSON = TEMPLATES_DIR / "templates.json"


# --- Pydantic Models ---
class TemplateInfo(BaseModel):
    """Template metadata for API response."""

    id: str
    name: str
    description: str
    category: str
    tags: list[str]
    tool_type: str


class CategoryInfo(BaseModel):
    """Category metadata for API response."""

    name: str
    description: str


class TemplatesResponse(BaseModel):
    """Response model for template list."""

    templates: list[TemplateInfo]
    categories: dict[str, CategoryInfo]


class AddTemplateRequest(BaseModel):
    """Request model for adding a template as a tool."""

    custom_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=NAME_MAX_LENGTH,
        description="Custom name for the tool (optional)",
    )


# --- Helper Functions ---
# テンプレートデータのキャッシュ
_templates_cache: dict[str, Any] | None = None


def load_templates_data() -> dict[str, Any]:
    """Load templates.json data with caching.

    Returns:
        Parsed JSON data containing templates and categories.

    Raises:
        HTTPException: If templates configuration file is not found or invalid.

    """
    global _templates_cache

    # キャッシュがあれば返す
    if _templates_cache is not None:
        return _templates_cache

    if not TEMPLATES_JSON.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Templates configuration not found",
        )
    try:
        with open(TEMPLATES_JSON, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
            _templates_cache = data
            return data
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Invalid templates configuration: {e}",
        )


def clear_templates_cache() -> None:
    """Clear templates data cache. Useful for testing."""
    global _templates_cache
    _templates_cache = None


def validate_template_file_path(file_path: str) -> Path:
    """Validate template file path to prevent directory traversal attacks.

    Args:
        file_path: Relative file path from templates directory.

    Returns:
        Resolved absolute path to the template file.

    Raises:
        HTTPException: If path validation fails.

    """
    # ".." や絶対パスを拒否
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template file path",
        )

    template_file = TEMPLATES_DIR / file_path

    # シンボリックリンク攻撃対策: 実際のパスがテンプレートディレクトリ配下であることを確認
    try:
        real_path = template_file.resolve()
        real_base = TEMPLATES_DIR.resolve()
        # relative_toはクロスプラットフォーム対応で堅牢
        real_path.relative_to(real_base)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid template file path: path traversal detected",
        )
    except OSError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve template file path",
        )

    return template_file


# --- API Endpoints ---
@router.get("/", response_model=TemplatesResponse)
def list_templates() -> TemplatesResponse:
    """Get all available templates.

    Returns:
        List of templates and categories.

    """
    data = load_templates_data()

    templates = [
        TemplateInfo(
            id=t["id"],
            name=t["name"],
            description=t["description"],
            category=t["category"],
            tags=t["tags"],
            tool_type=t["tool_type"],
        )
        for t in data["templates"]
    ]

    categories = {k: CategoryInfo(**v) for k, v in data["categories"].items()}

    return TemplatesResponse(templates=templates, categories=categories)


@router.post("/{template_id}/add", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def add_template_as_tool(
    template_id: str,
    request: AddTemplateRequest = Body(default=AddTemplateRequest()),
    session: Session = Depends(get_session),
) -> ToolRead:
    """Add a template as a new tool.

    Args:
        template_id: ID of the template to add.
        request: Optional request body with custom name.
        session: Database session.

    Returns:
        Created tool data.

    Raises:
        HTTPException: If template not found or creation fails.

    """
    data = load_templates_data()

    # テンプレートを検索
    template = next((t for t in data["templates"] if t["id"] == template_id), None)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    # テンプレートファイルのパスを検証
    template_file = validate_template_file_path(template["file"])

    # HTMLコンテンツを読み込み
    if not template_file.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Template file not found",
        )

    try:
        html_content = template_file.read_text(encoding="utf-8")
    except OSError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read template file: {e}",
        )

    # ツール名を決定（カスタム名があればそれを使用）
    tool_name = request.custom_name if request.custom_name else template["name"]

    # ToolCreateモデルを作成
    tool_data = ToolCreate(
        name=tool_name,
        description=template["description"],
        tags=template["tags"],
        html_content=html_content,
        tool_type=template["tool_type"],
    )

    # ツールを作成
    repo = ToolRepository(session)
    try:
        created_tool = repo.create_tool_with_content(tool_data)
        return ToolRead.model_validate(created_tool)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
