import os
import uuid
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, cast
from sqlmodel import Session, select, text

from html_tool_manager.models import Tool, ToolCreate


class SortOrder(str, Enum):
    """Enum defining sort order for search results."""

    RELEVANCE = "relevance"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    UPDATED_ASC = "updated_asc"
    UPDATED_DESC = "updated_desc"


class ToolRepository:
    """Repository class encapsulating database operations for tools."""

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: The database session.

        """
        self.session = session

    def create_tool(self, tool: Tool) -> Tool:
        """Create a new tool in the database."""
        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        return tool

    def create_tool_with_content(self, tool_data: ToolCreate) -> Tool:
        """Save HTML content to a file and create the tool in the database."""
        if not tool_data.html_content:
            # この関数ではhtml_contentが必須であると仮定
            raise ValueError("'html_content' is required.")

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

        # 既存のcreate_toolを呼び出す
        return self.create_tool(tool_to_db)

    def get_tool(self, tool_id: int) -> Optional[Tool]:
        """Get a single tool by ID."""
        return self.session.get(Tool, tool_id)

    def get_all_tools(self, offset: int = 0, limit: int = 100) -> List[Tool]:
        """Get all tools with pagination."""
        statement = select(Tool).order_by(Tool.updated_at.desc()).offset(offset).limit(limit)
        return self.session.exec(statement).all()

    def search_tools(
        self,
        parsed_query: Dict[str, List[str]],
        sort: SortOrder = SortOrder.RELEVANCE,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Tool]:
        """Search for tools with the specified query and sort order."""
        statement = select(Tool)  # ベースとなるクエリ

        # FTS検索条件の組み立て
        fts_query_parts = []
        if parsed_query.get("term"):
            # "term*" のようにクォートで囲む必要はない
            terms = " OR ".join([f"{term}*" for term in parsed_query["term"]])
            fts_query_parts.append(f"({terms})")
        if parsed_query.get("name"):
            # name:j* のようにクォートで囲まない
            terms = " OR ".join([f"{term}*" for term in parsed_query["name"]])
            fts_query_parts.append(f"name:{terms}")
        if parsed_query.get("desc"):
            terms = " OR ".join([f"{term}*" for term in parsed_query["desc"]])
            fts_query_parts.append(f"description:{terms}")

        # FTS仮想テーブルをTableオブジェクトとして定義 (rankカラムも定義)
        fts_metadata = MetaData()
        tool_fts_table = Table("tool_fts", fts_metadata, Column("rowid", Integer), Column("rank", Float))

        if fts_query_parts:
            fts_match_query = " ".join(fts_query_parts)
            statement = (
                statement.join(tool_fts_table, Tool.id == tool_fts_table.c.rowid)
                .where(text(f"{tool_fts_table.name} MATCH :fts_query"))
                .params(fts_query=fts_match_query)
            )

        # タグ検索条件
        if parsed_query.get("tag"):
            for tag_query in parsed_query["tag"]:
                statement = statement.where(cast(Tool.tags, String).like(f"%{tag_query}%"))

        # ソート順
        if sort == SortOrder.RELEVANCE and fts_query_parts:
            # FTSのrankは小さいほど関連性が高いので ASC
            statement = statement.order_by(tool_fts_table.c.rank.asc())
        elif sort == SortOrder.NAME_ASC:
            statement = statement.order_by(Tool.name.asc())
        elif sort == SortOrder.NAME_DESC:
            statement = statement.order_by(Tool.name.desc())
        elif sort == SortOrder.UPDATED_ASC:
            statement = statement.order_by(Tool.updated_at.asc())
        elif sort == SortOrder.UPDATED_DESC:
            statement = statement.order_by(Tool.updated_at.desc())
        else:
            statement = statement.order_by(Tool.updated_at.desc())  # デフォルトソート

        statement = statement.offset(offset).limit(limit)

        results = self.session.exec(statement).all()
        return results

    def update_tool(self, tool_id: int, tool_update: Tool) -> Optional[Tool]:
        """Update existing tool information."""
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
        """Delete a tool."""
        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None
        self.session.delete(tool)
        self.session.commit()
        return tool
