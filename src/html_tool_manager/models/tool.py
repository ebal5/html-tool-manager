import re
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import field_validator
from sqlmodel import JSON, Column, Field, SQLModel

# 制御文字のパターン
# 許可: \t (0x09), \n (0x0a)
# 禁止: \r (0x0d) を含む他の制御文字 - Windows改行(\r\n)は\nのみに正規化される想定
CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# バリデーション定数
NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 1000
TAG_MIN_LENGTH = 1
TAG_MAX_LENGTH = 50
TAGS_MAX_COUNT = 20


class ToolType(str, Enum):
    """Enum defining tool types."""

    HTML = "html"
    REACT = "react"


class ToolBase(SQLModel):
    """Base model representing basic tool information."""

    name: str = Field(index=True, min_length=NAME_MIN_LENGTH, max_length=NAME_MAX_LENGTH)
    description: Optional[str] = Field(default=None, max_length=DESCRIPTION_MAX_LENGTH)
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    filepath: Optional[str] = None  # APIリクエスト時にはオプショナル
    tool_type: Optional[ToolType] = Field(default=ToolType.HTML)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """名前のバリデーション：トリム、制御文字チェック。"""
        if v is None:
            raise ValueError("名前は必須です")
        v = v.strip()
        if not v:
            raise ValueError("名前は空にできません")
        if CONTROL_CHARS_PATTERN.search(v):
            raise ValueError("名前に制御文字を含めることはできません")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """説明のバリデーション：制御文字チェック（改行・タブは許可）。"""
        if v is None:
            return v
        if CONTROL_CHARS_PATTERN.search(v):
            raise ValueError("説明に制御文字を含めることはできません")
        return v

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """タグのバリデーション：数、長さ、制御文字チェック。"""
        if v is None:
            return []
        if not isinstance(v, list):
            raise ValueError("タグはリストで指定してください")
        if len(v) > TAGS_MAX_COUNT:
            raise ValueError(f"タグは最大{TAGS_MAX_COUNT}個までです")

        validated_tags = []
        for tag in v:
            if not isinstance(tag, str):
                raise ValueError("タグは文字列で指定してください")
            tag = tag.strip()
            if not tag:
                # 空文字やスペースのみのタグは暗黙的に除外される
                # 例: ["tag1", "", "  ", "tag2"] → ["tag1", "tag2"]
                continue
            if len(tag) < TAG_MIN_LENGTH or len(tag) > TAG_MAX_LENGTH:
                raise ValueError(f"各タグは{TAG_MIN_LENGTH}〜{TAG_MAX_LENGTH}文字で指定してください")
            if CONTROL_CHARS_PATTERN.search(tag):
                raise ValueError("タグに制御文字を含めることはできません")
            validated_tags.append(tag)

        return validated_tags


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
    tool_type: Optional[ToolType] = None  # 自動検出を許可するため Optional


class ToolRead(ToolBase):
    """Data model for API output when returning tool information."""

    id: int
    filepath: str
    created_at: datetime
    updated_at: datetime
