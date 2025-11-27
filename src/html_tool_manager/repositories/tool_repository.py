from typing import List, Optional, Dict
from enum import Enum

from sqlmodel import Session, select, text, column, table, func
from sqlalchemy import cast, String

from html_tool_manager.models import Tool

class SortOrder(str, Enum):
    RELEVANCE = "relevance"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    UPDATED_ASC = "updated_asc"
    UPDATED_DESC = "updated_desc"

class ToolRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_tool(self, tool: Tool) -> Tool:
        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        return tool

    def get_tool(self, tool_id: int) -> Optional[Tool]:
        return self.session.get(Tool, tool_id)

    def get_all_tools(self, offset: int = 0, limit: int = 100) -> List[Tool]:
        statement = select(Tool).order_by(Tool.updated_at.desc()).offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def search_tools(
        self,
        parsed_query: Dict[str, List[str]],
        sort: SortOrder = SortOrder.RELEVANCE,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Tool]:
        
        statement = select(Tool)
        
        # FTS検索条件の組み立て
        fts_queries = []
        if parsed_query.get("term"):
            terms = [f'{term}*' for term in parsed_query["term"]]
            fts_queries.append(" ".join(terms))
        if parsed_query.get("name"):
            terms = [f'name:{term}*' for term in parsed_query["name"]]
            fts_queries.extend(terms)
        if parsed_query.get("desc"):
            terms = [f'description:{term}*' for term in parsed_query["desc"]]
            fts_queries.extend(terms)

        if fts_queries:
            fts_match_query = " ".join(fts_queries)
            tool_fts = table("tool_fts", column("rowid"), column("rank"))
            
            statement = select(Tool, tool_fts.c.rank).join(
                tool_fts, Tool.id == tool_fts.c.rowid
            ).where(
                text("tool_fts MATCH :fts_query").params(fts_query=fts_match_query)
            )
        else:
            statement = select(Tool, text("0 as rank"))


        # タグ検索条件
        if parsed_query.get("tag"):
            for tag_query in parsed_query["tag"]:
                statement = statement.where(cast(Tool.tags, String).like(f"%{tag_query}%"))

        # ソート順
        if sort == SortOrder.RELEVANCE and fts_queries:
            statement = statement.order_by(text("rank"))
        elif sort == SortOrder.NAME_ASC:
            statement = statement.order_by(Tool.name.asc())
        elif sort == SortOrder.NAME_DESC:
            statement = statement.order_by(Tool.name.desc())
        elif sort == SortOrder.UPDATED_ASC:
            statement = statement.order_by(Tool.updated_at.asc())
        elif sort == SortOrder.UPDATED_DESC:
            statement = statement.order_by(Tool.updated_at.desc())
        else:
            statement = statement.order_by(Tool.updated_at.desc())
        
        statement = statement.offset(offset).limit(limit)
        
        results = self.session.exec(statement).all()
        return [tool for tool, rank in results]

    def update_tool(self, tool_id: int, tool_update: Tool) -> Optional[Tool]:
        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None
        
        tool_data = tool_update.model_dump(exclude_unset=True)
        for key, value in tool_data.items():
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
