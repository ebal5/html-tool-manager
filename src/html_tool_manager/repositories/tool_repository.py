import os
import shutil
import uuid
from enum import Enum
from typing import Dict, List, Optional

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, cast
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select, text

from html_tool_manager.core.config import app_settings
from html_tool_manager.core.file_utils import atomic_write_file
from html_tool_manager.core.security import is_path_within_base
from html_tool_manager.models import Tool, ToolCreate
from html_tool_manager.models.tool import ToolType
from html_tool_manager.templates.react_template import generate_react_html
from html_tool_manager.utils.code_detector import detect_tool_type


class SortOrder(str, Enum):
    """Enum defining sort order for search results."""

    RELEVANCE = "relevance"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    UPDATED_ASC = "updated_asc"
    UPDATED_DESC = "updated_desc"


def _escape_fts5_term(term: str) -> str:
    """Escape special characters for FTS5 query.

    FTS5では特殊文字をダブルクォートで囲むことでリテラルとして扱える。
    ダブルクォート自体は "" でエスケープする。
    制御文字（特にnull byte）はSQLiteエラーの原因となるため除去する。

    Args:
        term: The search term to escape.

    Returns:
        Escaped term safe for FTS5 query, with wildcard suffix.
        Returns empty string for invalid terms (empty, incomplete field prefix, etc.).

    """
    # 空文字列や空白のみの場合はスキップ
    if not term or not term.strip():
        return ""

    # 制御文字を除去（null byte等がSQLiteエラーの原因となる）
    # 0x20未満の制御文字（\t, \n, null byte等）は検索クエリでは不要なので除去
    term = "".join(c for c in term if ord(c) >= 0x20)

    # 既に末尾が * の場合は除去（後で追加するため）
    term = term.rstrip("*")
    if not term:
        return ""

    # 不完全なフィールドプレフィックス（例: "tag:", "name:"）をスキップ
    # これらはFTS5でカラム指定子として解釈されエラーの原因となる
    if term.endswith(":") and term[:-1].isalpha():
        return ""

    # ダブルクォートをエスケープ
    escaped = term.replace('"', '""')

    # ダブルクォートで囲んで、接頭辞検索用の * を追加
    return f'"{escaped}"*'


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

        # 自動検出（ユーザーが明示的に指定していない場合）
        if tool_data.tool_type is None:
            tool_data.tool_type = detect_tool_type(tool_data.html_content)

        # React タイプの場合はテンプレートでラップ
        if tool_data.tool_type == ToolType.REACT:
            final_html = generate_react_html(tool_data.html_content)
        else:
            final_html = tool_data.html_content

        # 一意のディレクトリとファイルパスを生成
        tool_dir = f"{app_settings.tools_dir}/{uuid.uuid4()}"
        # 明示的な権限でディレクトリを作成（owner: rwx, group/other: rx）
        os.makedirs(tool_dir, mode=0o755, exist_ok=True)
        final_filepath = f"{tool_dir}/index.html"

        # ファイルを原子的に作成し、明示的な権限を設定（owner: rw, group/other: r）
        atomic_write_file(final_filepath, final_html, mode=0o644)

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
        statement = select(Tool).order_by(Tool.updated_at.desc()).offset(offset).limit(limit)  # type: ignore[attr-defined]
        return list(self.session.exec(statement).all())

    def search_tools(
        self,
        parsed_query: Dict[str, List[str]],
        sort: SortOrder = SortOrder.RELEVANCE,
        offset: int = 0,
        limit: int = 100,
    ) -> List[Tool]:
        """Search for tools with the specified query and sort order."""
        statement = select(Tool)  # ベースとなるクエリ

        # FTS検索条件の組み立て（特殊文字をエスケープ）
        fts_query_parts = []
        if parsed_query.get("term"):
            escaped_terms = [_escape_fts5_term(t) for t in parsed_query["term"]]
            escaped_terms = [t for t in escaped_terms if t]  # 空文字を除去
            if escaped_terms:
                terms = " OR ".join(escaped_terms)
                fts_query_parts.append(f"({terms})")
        if parsed_query.get("name"):
            escaped_terms = [_escape_fts5_term(t) for t in parsed_query["name"]]
            escaped_terms = [t for t in escaped_terms if t]
            if escaped_terms:
                terms = " OR ".join(escaped_terms)
                fts_query_parts.append(f"name:{terms}")
        if parsed_query.get("desc"):
            escaped_terms = [_escape_fts5_term(t) for t in parsed_query["desc"]]
            escaped_terms = [t for t in escaped_terms if t]
            if escaped_terms:
                terms = " OR ".join(escaped_terms)
                fts_query_parts.append(f"description:{terms}")

        # FTS仮想テーブルをTableオブジェクトとして定義 (rankカラムも定義)
        fts_metadata = MetaData()
        tool_fts_table = Table("tool_fts", fts_metadata, Column("rowid", Integer), Column("rank", Float))

        if fts_query_parts:
            fts_match_query = " ".join(fts_query_parts)
            join_condition: ColumnElement[bool] = Tool.id == tool_fts_table.c.rowid  # type: ignore[assignment]
            statement = (
                statement.join(tool_fts_table, join_condition)
                .where(text(f"{tool_fts_table.name} MATCH :fts_query"))
                .params(fts_query=fts_match_query)
            )

        # タグ検索条件（LIKEワイルドカード文字をエスケープ）
        if parsed_query.get("tag"):
            for tag_query in parsed_query["tag"]:
                escaped_tag = self._escape_like_pattern(tag_query)
                statement = statement.where(cast(Tool.tags, String).like(f"%{escaped_tag}%", escape="\\"))

        # ソート順
        if sort == SortOrder.RELEVANCE and fts_query_parts:
            # FTSのrankは小さいほど関連性が高いので ASC
            statement = statement.order_by(tool_fts_table.c.rank.asc())
        elif sort == SortOrder.NAME_ASC:
            statement = statement.order_by(Tool.name.asc())  # type: ignore[attr-defined]
        elif sort == SortOrder.NAME_DESC:
            statement = statement.order_by(Tool.name.desc())  # type: ignore[attr-defined]
        elif sort == SortOrder.UPDATED_ASC:
            statement = statement.order_by(Tool.updated_at.asc())  # type: ignore[attr-defined]
        elif sort == SortOrder.UPDATED_DESC:
            statement = statement.order_by(Tool.updated_at.desc())  # type: ignore[attr-defined]
        else:
            statement = statement.order_by(Tool.updated_at.desc())  # type: ignore[attr-defined]

        statement = statement.offset(offset).limit(limit)

        results = self.session.exec(statement).all()
        return list(results)

    def update_tool(self, tool_id: int, tool_update: Tool, *, expected_version: int) -> Optional[Tool]:
        """Update existing tool information with optimistic locking.

        Args:
            tool_id: The ID of the tool to update.
            tool_update: The updated tool data.
            expected_version: The expected version for optimistic locking.

        Returns:
            The updated tool, or None if not found.

        Raises:
            OptimisticLockError: If the expected version doesn't match the current version.

        """
        from datetime import datetime, timezone

        from html_tool_manager.core.exceptions import OptimisticLockError

        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None

        # 楽観的ロックチェック
        if tool.version != expected_version:
            raise OptimisticLockError(tool.version, expected_version)

        tool_data = tool_update.model_dump(exclude_unset=True)
        for key, value in tool_data.items():
            setattr(tool, key, value)

        # updated_atを現在時刻に更新
        tool.updated_at = datetime.now(timezone.utc)
        # バージョンをインクリメント
        tool.version += 1

        self.session.add(tool)
        self.session.commit()
        self.session.refresh(tool)
        return tool

    def delete_tool(self, tool_id: int) -> Optional[Tool]:
        """Delete a tool and its associated files."""
        tool = self.session.get(Tool, tool_id)
        if not tool:
            return None

        # filepathを保存（DBから削除後にファイル削除するため）
        filepath = tool.filepath

        # 先にDBから削除（コミット成功後にファイル削除）
        self.session.delete(tool)
        self.session.commit()

        # DBコミット成功後にファイルとディレクトリを削除
        # これによりDB削除失敗時にファイルだけ消える問題を防ぐ
        if filepath:
            tool_dir = os.path.dirname(filepath)
            tools_dir = app_settings.tools_dir
            # シンボリックリンク攻撃を防止: 実際のパスがtools_dir配下であることを確認
            try:
                if not is_path_within_base(tool_dir, tools_dir):
                    # パストラバーサル攻撃の可能性 - 削除をスキップ
                    pass
                elif os.path.exists(tool_dir) and os.path.isdir(tool_dir):
                    shutil.rmtree(tool_dir)
            except OSError:
                # ファイル削除に失敗してもログのみ（DBは既に削除済み）
                pass

        return tool

    @staticmethod
    def _escape_like_pattern(value: str) -> str:
        r"""Escape special characters for SQL LIKE pattern.

        SQLAlchemyのcontains/startswith/endswithのautoescape実装に準拠。
        エスケープ文字として'\'を使用。

        Args:
            value: The string to escape.

        Returns:
            Escaped string safe for use in LIKE pattern.

        """
        # エスケープ文字自体を先にエスケープし、その後ワイルドカード文字をエスケープ
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def get_tag_suggestions(self, query: str = "", limit: int = 20) -> List[str]:
        """Get tag suggestions based on existing tags.

        Args:
            query: Search query to filter tags (case-insensitive partial match).
            limit: Maximum number of suggestions to return.

        Returns:
            List of unique tags matching the query, sorted by frequency (most common first).

        """
        # SQLiteのjson_each関数を使用してタグを集計
        # これにより全ツールをメモリに読み込まずにDB側で処理できる
        # ESCAPE句でワイルドカード文字のエスケープを有効化
        sql = text("""
            SELECT tag.value as tag_name, COUNT(*) as tag_count
            FROM tool, json_each(tool.tags) as tag
            WHERE LOWER(tag.value) LIKE LOWER(:pattern) ESCAPE '\\'
            GROUP BY tag.value
            ORDER BY tag_count DESC, tag_name ASC
            LIMIT :limit
        """)

        escaped_query = self._escape_like_pattern(query)
        pattern = f"%{escaped_query}%" if query else "%"
        result = self.session.execute(sql, {"pattern": pattern, "limit": limit})
        return [row[0] for row in result.fetchall()]
