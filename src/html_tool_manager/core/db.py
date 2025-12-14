from typing import Generator

from sqlmodel import Session, SQLModel, create_engine, text

from html_tool_manager.models.snapshot import ToolSnapshot  # noqa: F401

DATABASE_URL = "sqlite:///./tools.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    """データベースとテーブルを作成し、FTS5仮想テーブルをセットアップします。"""
    SQLModel.metadata.create_all(engine)

    # FTS5仮想テーブルの作成（存在しない場合のみ）
    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS tool_fts
            USING fts5(name, description, content='tool', content_rowid='id')
        """)
        )

        # トリガーの作成（INSERTとUPDATEとDELETE用）
        conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS tool_ai AFTER INSERT ON tool BEGIN
                INSERT INTO tool_fts(rowid, name, description)
                VALUES (new.id, new.name, new.description);
            END
        """)
        )
        conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS tool_ad AFTER DELETE ON tool BEGIN
                INSERT INTO tool_fts(tool_fts, rowid, name, description)
                VALUES ('delete', old.id, old.name, old.description);
            END
        """)
        )
        conn.execute(
            text("""
            CREATE TRIGGER IF NOT EXISTS tool_au AFTER UPDATE ON tool BEGIN
                INSERT INTO tool_fts(tool_fts, rowid, name, description)
                VALUES ('delete', old.id, old.name, old.description);
                INSERT INTO tool_fts(rowid, name, description)
                VALUES (new.id, new.name, new.description);
            END
        """)
        )
        conn.commit()


def get_session() -> Generator[Session, None, None]:
    """FastAPIの依存性注入用にデータベースセッションを提供します。"""
    with Session(engine) as session:
        yield session
