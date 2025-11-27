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
    repo = ToolRepository(session)
    
    if not tool_data.filepath and not tool_data.html_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either 'filepath' or 'html_content' must be provided.")
    if tool_data.filepath and tool_data.html_content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide either 'filepath' or 'html_content', not both.")

    if tool_data.html_content:
        tool_dir = f"static/tools/{uuid.uuid4()}"
        os.makedirs(tool_dir, exist_ok=True)
        final_filepath = f"{tool_dir}/index.html"
        with open(final_filepath, "w") as f:
            f.write(tool_data.html_content)
        tool_data.filepath = final_filepath
    
    # ToolCreateからToolオブジェクトを作成
    tool_to_db = Tool.model_validate(tool_data)
    created_tool = repo.create_tool(tool_to_db)
    return created_tool

@router.get("/", response_model=List[ToolRead])
def read_tools(
    session: Session = Depends(get_session),
    q: str = Query(None, description="Search query with optional prefixes like 'name:', 'desc:', 'tag:'"),
    sort: SortOrder = Query(SortOrder.RELEVANCE, description="Sort order"),
    offset: int = 0,
    limit: int = 100,
):
    repo = ToolRepository(session)
    if q:
        parsed_query = parse_query(q)
        tools = repo.search_tools(parsed_query, sort=sort, offset=offset, limit=limit)
    else:
        # ソート順をget_all_toolsにも適用できるように修正が必要だが、一旦保留
        tools = repo.get_all_tools(offset=offset, limit=limit)
    return tools

@router.get("/{tool_id}", response_model=List[ToolRead])
def read_tool(tool_id: int, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tool = repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return tool

@router.put("/{tool_id}", response_model=ToolRead)
def update_tool(tool_id: int, tool_data: ToolCreate, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tool_to_update = repo.get_tool(tool_id)
    if not tool_to_update:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    
    update_data = tool_data.model_dump(exclude_unset=True)
    tool_to_update.sqlmodel_update(update_data)
    
    updated_tool = repo.update_tool(tool_id, tool_to_update)
    return updated_tool

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(tool_id: int, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tool = repo.delete_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return {"message": "Tool deleted successfully"}
