import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session

from html_tool_manager.core.db import get_session
from html_tool_manager.models import ToolCreate, ToolRead, Tool
from html_tool_manager.repositories import ToolRepository, SortOrder
from .query_parser import parse_query

router = APIRouter(prefix="/tools", tags=["tools"])

@router.post("/", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def create_tool(tool_data: ToolCreate, session: Session = Depends(get_session)):
    """新しいツールを作成します。"""
    repo = ToolRepository(session)
    
    # html_contentが必須であることを検証
    if not tool_data.html_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="'html_content' is required.")

    # 一意のディレクトリとファイルパスを生成
    tool_dir = f"static/tools/{uuid.uuid4()}"
    os.makedirs(tool_dir, exist_ok=True)
    final_filepath = f"{tool_dir}/index.html"
    
    with open(final_filepath, "w") as f:
        f.write(tool_data.html_content)
    
    # DBに保存するモデルのfilepathを更新
    tool_data.filepath = final_filepath
    
    # ToolCreateからToolオブジェクトを作成
    tool_to_db = Tool.model_validate(tool_data)
    created_tool = repo.create_tool(tool_to_db)
    return created_tool

@router.get("/", response_model=List[ToolRead])
def read_tools(
    session: Session = Depends(get_session),
    q: str = Query(None, description="検索クエリ（例: 'name:', 'desc:', 'tag:'）"),
    sort: SortOrder = Query(SortOrder.RELEVANCE, description="ソート順"),
    offset: int = 0,
    limit: int = 100,
):
    """ツールの一覧を取得、または検索します。"""
    repo = ToolRepository(session)
    if q:
        parsed_query = parse_query(q)
        tools = repo.search_tools(parsed_query, sort=sort, offset=offset, limit=limit)
    else:
        tools = repo.get_all_tools(offset=offset, limit=limit)
    
    # ToolReadモデルを使って明示的にレスポンスを構築
    return [ToolRead.model_validate(tool) for tool in tools]

@router.get("/{tool_id}", response_model=ToolRead)
def read_tool(tool_id: int, session: Session = Depends(get_session)):
    """IDを指定して単一のツールを取得します。"""
    repo = ToolRepository(session)
    db_tool = repo.get_tool(tool_id)
    if not db_tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    
    # ToolReadモデルを使って明示的にレスポンスを構築
    return ToolRead.model_validate(db_tool)

@router.put("/{tool_id}", response_model=ToolRead)
def update_tool(tool_id: int, tool_data: ToolCreate, session: Session = Depends(get_session)):
    """既存のツールを更新します。"""
    repo = ToolRepository(session)
    tool_to_update = repo.get_tool(tool_id)
    if not tool_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")

    # html_contentが提供された場合は、既存のファイルを上書き
    if tool_data.html_content is not None:
        # アプリによって作成された安全なパスであることを前提とする
        with open(tool_to_update.filepath, "w") as f:
            f.write(tool_data.html_content)

    # メタデータを更新
    update_data = tool_data.model_dump(exclude_unset=True, exclude={'html_content'})
    tool_to_update.sqlmodel_update(update_data)
    
    updated_tool = repo.update_tool(tool_id, tool_to_update)
    return updated_tool

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(tool_id: int, session: Session = Depends(get_session)):
    """ツールを削除します。"""
    repo = ToolRepository(session)
    tool = repo.delete_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    # 204 No Contentのため、このレスポンスボディは実際にはクライアントに送信されない
    return {"message": "Tool deleted successfully"}