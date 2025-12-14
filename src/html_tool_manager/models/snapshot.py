"""Snapshot model for tool version history."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from .tool import CONTROL_CHARS_PATTERN

# バリデーション定数
SNAPSHOT_NAME_MAX_LENGTH = 100
MAX_SNAPSHOTS_PER_TOOL = 20
MAX_CONTENT_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


class SnapshotType(str, Enum):
    """Enum defining snapshot types."""

    AUTO = "auto"
    MANUAL = "manual"


class SnapshotBase(SQLModel):
    """Base model for snapshot data."""

    name: Optional[str] = Field(default=None, max_length=SNAPSHOT_NAME_MAX_LENGTH)
    snapshot_type: SnapshotType = Field(default=SnapshotType.AUTO)

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """スナップショット名のバリデーション。"""
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if len(v) > SNAPSHOT_NAME_MAX_LENGTH:
            raise ValueError(f"名前は{SNAPSHOT_NAME_MAX_LENGTH}文字以内で入力してください")
        if CONTROL_CHARS_PATTERN.search(v):
            raise ValueError("名前に制御文字を含めることはできません")
        return v


class ToolSnapshot(SnapshotBase, table=True):
    """Snapshot model stored in the database."""

    __tablename__ = "tool_snapshot"

    id: Optional[int] = Field(default=None, primary_key=True)
    tool_id: int = Field(foreign_key="tool.id", index=True, nullable=False)
    html_content: str = Field(nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )


class SnapshotCreate(SnapshotBase):
    """Data model for API input when creating a snapshot."""

    pass  # name, snapshot_type を継承


class SnapshotRead(SnapshotBase):
    """Data model for API output when returning snapshot information (without content)."""

    id: int
    tool_id: int
    created_at: datetime


class SnapshotReadWithContent(SnapshotRead):
    """Data model for API output including full content."""

    html_content: str
