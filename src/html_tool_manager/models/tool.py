from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel, Column, JSON


class ToolBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    filepath: Optional[str] = None # オプショナルに変更

class Tool(ToolBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filepath: str # DBには必ずfilepathを保存するので、こちらは必須のまま
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# Pydanticスキーマ
class ToolCreate(ToolBase):
    html_content: Optional[str] = None # 追加

class ToolRead(ToolBase):
    id: int
    filepath: str # filepathをレスポンスに含める
    created_at: datetime
    updated_at: datetime
