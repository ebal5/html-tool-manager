"""データベースマイグレーションスクリプト: tool_type カラムを追加

既存の tool テーブルに tool_type カラムを追加し、
既存のレコードにはデフォルト値 'html' を設定します。
"""

import sqlite3
import sys
from pathlib import Path

# プロジェクトルートを取得
project_root = Path(__file__).parent.parent
db_path = project_root / "tools.db"

if not db_path.exists():
    print(f"エラー: データベースファイルが見つかりません: {db_path}")
    sys.exit(1)

print(f"データベース: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # tool_type カラムが既に存在するか確認
    cursor.execute("PRAGMA table_info(tool)")
    columns = [col[1] for col in cursor.fetchall()]

    if "tool_type" in columns:
        print("tool_type カラムは既に存在します。マイグレーションをスキップします。")
    else:
        print("tool_type カラムを追加しています...")
        cursor.execute("ALTER TABLE tool ADD COLUMN tool_type TEXT DEFAULT 'html'")
        conn.commit()
        print("✓ tool_type カラムを追加しました。")

        # 既存レコード数を確認
        cursor.execute("SELECT COUNT(*) FROM tool")
        count = cursor.fetchone()[0]
        print(f"✓ {count} 件のレコードに tool_type='html' が設定されました。")

    conn.close()
    print("マイグレーション完了！")

except sqlite3.Error as e:
    print(f"エラー: {e}")
    sys.exit(1)
