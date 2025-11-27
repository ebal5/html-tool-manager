from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import Field, SQLModel, Column, JSON


class ToolBase(SQLModel):
    """ツールの基本情報を表すベースモデル。"""
    name: str = Field(index=True)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    filepath: Optional[str] = None # APIリクエスト時にはオプショナル

class Tool(ToolBase, table=True):
    """データベースに保存されるツールモデル。"""
    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str # DB上では必須
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)

# APIの入出力のためのPydanticモデル
class ToolCreate(ToolBase):
    """ツール作成時にAPIが受け取るデータモデル。"""
    html_content: Optional[str] = None # HTMLコンテンツの直接貼り付け用

class ToolRead(ToolBase):
    """ツール情報をAPIが返す際のデータモデル。"""
    id: int
    filepath: str
    created_at: datetime
    updated_at: datetime