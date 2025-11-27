from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel, Column, JSON


class ToolBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    # `sa_column` を使って、このフィールドがJSON型であることを明示的に指定する
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    filepath: str # ツール本体のファイルパス（HTMLファイルなど）

class Tool(ToolBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

# Optional: Pydanticスキーマも定義しておくと便利
class ToolCreate(ToolBase):
    pass

class ToolRead(ToolBase):
    id: int
    created_at: datetime
    updated_at: datetime
