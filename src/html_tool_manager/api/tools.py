import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from html_tool_manager.core.db import get_session
from html_tool_manager.models import ToolCreate, ToolRead
from html_tool_manager.repositories import ToolRepository

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
        # Update the filepath on the input model itself
        tool_data.filepath = final_filepath
    
    created_tool = repo.create_tool(tool_data)
    return created_tool

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
