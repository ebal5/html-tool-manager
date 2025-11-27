from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from html_tool_manager.core.db import get_session
from html_tool_manager.models import Tool, ToolCreate, ToolRead
from html_tool_manager.repositories import ToolRepository

router = APIRouter(prefix="/tools", tags=["tools"])

@router.post("/", response_model=ToolRead, status_code=status.HTTP_201_CREATED)
def create_tool(tool: ToolCreate, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    db_tool = repo.create_tool(tool)
    return db_tool

@router.get("/", response_model=List[ToolRead])
def read_tools(offset: int = 0, limit: int = 100, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tools = repo.get_all_tools(offset=offset, limit=limit)
    return tools

@router.get("/{tool_id}", response_model=ToolRead)
def read_tool(tool_id: int, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tool = repo.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return tool

@router.put("/{tool_id}", response_model=ToolRead)
def update_tool(tool_id: int, tool: ToolCreate, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    db_tool = repo.update_tool(tool_id, tool)
    if not db_tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return db_tool

@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tool(tool_id: int, session: Session = Depends(get_session)):
    repo = ToolRepository(session)
    tool = repo.delete_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tool not found")
    return {"message": "Tool deleted successfully"}
