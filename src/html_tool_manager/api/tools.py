from typing import List, Optional

import msgpack
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlmodel import Session

from html_tool_manager.core.config import app_settings
from html_tool_manager.core.db import get_session
from html_tool_manager.core.file_utils import atomic_write_file
from html_tool_manager.core.security import is_path_within_base
from html_tool_manager.models import SnapshotType, ToolCreate, ToolRead
from html_tool_manager.models.tool import NAME_MAX_LENGTH
from html_tool_manager.repositories import SnapshotRepository, SortOrder, ToolRepository

from .query_parser import parse_query

router = APIRouter(prefix="/tools", tags=["tools"])


# --- Pydantic Response/Request Models ---
class ToolExportRequest(BaseModel):
    """Request model for exporting tools."""

    tool_ids: List[int]


class ToolImportResponse(BaseModel):
    """Response model for tool import."""

    imported_count: int


class ToolForkRequest(BaseModel):
    """Request model for forking a tool."""

    name: Optional[str] = None  # 省略時は「{元の名前} (Fork)」


# インポートファイルの最大サイズ（10MB）
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024


def validate_tool_filepath(filepath: str | None) -> str:
    r"""Validate tool filepath for security.

    Uses is_path_within_base with os.path.commonpath() for cross-platform
    path traversal detection. This is more robust than startswith() checks,
    especially on Windows where both '/' and '\\' are valid path separators.

    Args:
        filepath: The filepath to validate

    Returns:
        The validated filepath

    Raises:
        HTTPException: If the filepath is invalid or path traversal is detected

    """
    tools_dir = app_settings.tools_dir
    if not is_path_within_base(filepath or "", tools_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filepath",
        )

    return filepath  # type: ignore[return-value]


@router.post("/", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def create_tool(tool_data: ToolCreate, session: Session = Depends(get_session)) -> ToolRead:
    """Create a new tool."""
    repo = ToolRepository(session)
    try:
        created_tool = repo.create_tool_with_content(tool_data)
        return ToolRead.model_validate(created_tool)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=List[ToolRead])
def read_tools(
    session: Session = Depends(get_session),
    q: Optional[str] = Query(None, max_length=500, description="検索クエリ（例: 'name:', 'desc:', 'tag:'）"),
    sort: SortOrder = Query(SortOrder.RELEVANCE, description="ソート順"),
    offset: int = Query(default=0, ge=0, description="オフセット（0以上）"),
    limit: int = Query(default=100, ge=1, le=1000, description="取得件数（1-1000）"),
) -> List[ToolRead]:
    """Get a list of tools, or search for tools."""
    repo = ToolRepository(session)
    # クエリがない場合も空のdictでsearch_toolsを呼び、sortを適用
    parsed_query = parse_query(q) if q else {}
    tools = repo.search_tools(parsed_query, sort=sort, offset=offset, limit=limit)

    # ToolReadモデルを使って明示的にレスポンスを構築
    return [ToolRead.model_validate(tool) for tool in tools]


@router.get("/tags/suggest", response_model=List[str])
def suggest_tags(
    q: str = Query(default="", max_length=50, description="タグ検索クエリ（部分一致）"),
    session: Session = Depends(get_session),
) -> List[str]:
    """Get tag suggestions based on existing tags."""
    repo = ToolRepository(session)
    return repo.get_tag_suggestions(q)


@router.get("/{tool_id}", response_model=ToolRead)
def read_tool(tool_id: int, session: Session = Depends(get_session)) -> ToolRead:
    """Get a single tool by ID."""
    repo = ToolRepository(session)
    db_tool = repo.get_tool(tool_id)
    if not db_tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # ToolReadモデルを使って明示的にレスポンスを構築
    return ToolRead.model_validate(db_tool)


@router.put("/{tool_id}", response_model=ToolRead)
def update_tool(tool_id: int, tool_data: ToolCreate, session: Session = Depends(get_session)) -> ToolRead:
    """Update an existing tool."""
    repo = ToolRepository(session)
    tool_to_update = repo.get_tool(tool_id)
    if not tool_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # html_contentが提供された場合は、既存のファイルを上書き
    if tool_data.html_content is not None:
        from html_tool_manager.models.tool import ToolType
        from html_tool_manager.templates.react_template import generate_react_html

        # tool_type が React の場合はテンプレートでラップ
        if tool_data.tool_type == ToolType.REACT:
            final_html = generate_react_html(tool_data.html_content)
        else:
            final_html = tool_data.html_content

        # TOCTOU対策: ファイルパスを検証してシンボリックリンク攻撃を防止
        filepath = validate_tool_filepath(tool_to_update.filepath)

        # 現在の内容を読み取り、変更がある場合のみスナップショット作成
        try:
            with open(filepath, encoding="utf-8") as f:
                current_content = f.read()
            # 内容が変更されている場合のみスナップショット作成
            if current_content != final_html:
                snapshot_repo = SnapshotRepository(session)
                snapshot_repo.create_snapshot(
                    tool_id=tool_id,
                    html_content=current_content,
                    snapshot_type=SnapshotType.AUTO,
                )
        except FileNotFoundError:
            # ファイルが存在しない場合はスナップショット作成をスキップ
            pass
        except ValueError:
            # コンテンツサイズが上限を超える場合はスナップショット作成をスキップ
            pass

        try:
            atomic_write_file(filepath, final_html)
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Permission denied when writing file",
            )
        except OSError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write file: {e}",
            )

    # メタデータを更新（filepathは変更不可 - セキュリティのため既存の値を維持）
    update_data = tool_data.model_dump(exclude_unset=True, exclude={"html_content", "filepath"})
    tool_to_update.sqlmodel_update(update_data)

    # 存在確認は上で済んでいるため、update_toolは必ずToolを返す
    updated_tool = repo.update_tool(tool_id, tool_to_update)
    return ToolRead.model_validate(updated_tool)


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(tool_id: int, session: Session = Depends(get_session)) -> None:
    """Delete a tool and its associated snapshots."""
    repo = ToolRepository(session)

    # ツールの存在確認
    tool = repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # 関連スナップショットを先に削除
    snapshot_repo = SnapshotRepository(session)
    snapshot_repo.delete_all_by_tool(tool_id)

    # ツールを削除
    repo.delete_tool(tool_id)

    # 204 No Contentのため、レスポンスボディは返さない
    return None


@router.post("/{tool_id}/fork", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def fork_tool(
    tool_id: int,
    fork_request: ToolForkRequest,
    session: Session = Depends(get_session),
) -> ToolRead:
    """Fork an existing tool to create a copy."""
    repo = ToolRepository(session)

    # 1. 元ツールの取得
    original_tool = repo.get_tool(tool_id)
    if not original_tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # 2. HTMLコンテンツの読み取り（セキュリティ検証付き）
    filepath = validate_tool_filepath(original_tool.filepath)

    try:
        with open(filepath, encoding="utf-8") as f:
            html_content = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool file not found")
    except (PermissionError, OSError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read tool file due to permission or system error",
        )

    # 3. フォーク名の決定
    if fork_request.name and fork_request.name.strip():
        fork_name = fork_request.name.strip()
        # カスタム名の長さをチェック
        if len(fork_name) > NAME_MAX_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Name must be at most {NAME_MAX_LENGTH} characters",
            )
    else:
        suffix = " (Fork)"
        max_base_length = NAME_MAX_LENGTH - len(suffix)
        base_name = (
            original_tool.name[:max_base_length] if len(original_tool.name) > max_base_length else original_tool.name
        )
        fork_name = f"{base_name}{suffix}"

    # 4. ToolCreateの構築
    tool_create = ToolCreate(
        name=fork_name,
        description=original_tool.description,
        tags=original_tool.tags.copy() if original_tool.tags else [],
        html_content=html_content,
        tool_type=original_tool.tool_type,
    )

    # 5. フォークの作成
    try:
        forked_tool = repo.create_tool_with_content(tool_create)
        return ToolRead.model_validate(forked_tool)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/export", response_class=Response)
def export_tools(export_request: ToolExportRequest, session: Session = Depends(get_session)) -> Response:
    """Export selected tools in MessagePack format."""
    repo = ToolRepository(session)
    tools_to_export = []
    for tool_id in export_request.tool_ids:
        tool = repo.get_tool(tool_id)
        if tool:
            # HTMLコンテンツを読み込む
            try:
                with open(tool.filepath, "r", encoding="utf-8") as f:
                    html_content = f.read()
            except FileNotFoundError:
                # ファイルが見つからない場合はスキップ
                continue

            tool_data = {
                "name": tool.name,
                "description": tool.description,
                "tags": tool.tags,
                "html_content": html_content,
                "tool_type": tool.tool_type,
            }
            tools_to_export.append(tool_data)

    if not tools_to_export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No exportable tools found.")

    # MessagePackでシリアライズ
    packed_data = msgpack.packb(tools_to_export, use_bin_type=True)

    return Response(
        content=packed_data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="tools-export.pack"'},
    )


@router.post("/import", response_model=ToolImportResponse)
async def import_tools(file: UploadFile = File(...), session: Session = Depends(get_session)) -> ToolImportResponse:
    """Import tools from a MessagePack file."""
    if file.content_type != "application/octet-stream":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Unsupported file type.")

    # ファイルサイズの制限を確認（DoS対策: ストリーミングでサイズをチェック）
    # 一度にメモリに読み込まず、チャンクごとにチェックすることでOOMを防止
    contents = bytearray()
    chunk_size = 8192  # 8KB
    while chunk := await file.read(chunk_size):
        contents.extend(chunk)
        if len(contents) > MAX_IMPORT_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_IMPORT_FILE_SIZE // (1024 * 1024)}MB.",
            )
    contents_bytes = bytes(contents)

    try:
        tools_to_import = msgpack.unpackb(contents_bytes, raw=False)
    except (msgpack.UnpackException, ValueError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid MessagePack file: {e}")

    imported_count = 0
    repo = ToolRepository(session)
    for tool_data in tools_to_import:
        # ToolCreateモデルでバリデーション
        try:
            tool_create = ToolCreate(**tool_data)
            repo.create_tool_with_content(tool_create)
            imported_count += 1
        except (ValueError, Exception):  # Pydanticのバリデーションエラーなどもキャッチ
            # 不正なデータはスキップ
            continue

    return ToolImportResponse(imported_count=imported_count)
