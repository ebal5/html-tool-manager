from typing import List, Optional

from sqlmodel import Session, select

from html_tool_manager.models import Tool, ToolCreate


class ToolRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_tool(self, tool_create: ToolCreate) -> Tool:
        tool = Tool.model_validate(tool_create)
        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        return tool

    def get_tool(self, tool_id: int) -> Optional[Tool]:
        return self.session.get(Tool, tool_id)

    def get_all_tools(self, offset: int = 0, limit: int = 100) -> List[Tool]:
        statement = select(Tool).offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def update_tool(self, tool_id: int, tool_update: ToolCreate) -> Optional[Tool]:
        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None
        
        # Update specific fields
        for key, value in tool_update.model_dump(exclude_unset=True).items():
            setattr(tool, key, value)
        
        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        return tool

    def delete_tool(self, tool_id: int) -> Optional[Tool]:
        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None
        self.session.delete(tool)
        self.session.commit()
        return tool
