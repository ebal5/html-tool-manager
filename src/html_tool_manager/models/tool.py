from datetime import datetime, timezone
from typing import List, Optional

from sqlmodel import JSON, Column, Field, SQLModel


class ToolBase(SQLModel):
    """Base model representing basic tool information."""

    name: str = Field(index=True)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    filepath: Optional[str] = None  # APIリクエスト時にはオプショナル


class Tool(ToolBase, table=True):
    """Tool model stored in the database."""

    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str  # DB上では必須
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), nullable=False)


# APIの入出力のためのPydanticモデル
class ToolCreate(ToolBase):
    """Data model for API input when creating a tool."""

    html_content: Optional[str] = None  # HTMLコンテンツの直接貼り付け用


class ToolRead(ToolBase):
    """Data model for API output when returning tool information."""

    id: int
    filepath: str
    created_at: datetime
    updated_at: datetime
