"""Integration tests for backup API endpoints."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from html_tool_manager.core.backup import BackupService
from html_tool_manager.main import app


@pytest.fixture
def mock_backup_service(tmp_path: Path) -> BackupService:
    """Create a mock backup service with temporary directories."""
    db_path = tmp_path / "test.db"
    # Create actual SQLite database
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO test (value) VALUES ('test data')")
        conn.commit()

    backup_dir = tmp_path / "backups"
    return BackupService(str(db_path), str(backup_dir), max_generations=3)


@pytest.fixture
def client_with_backup(mock_backup_service: BackupService) -> TestClient:
    """Create a test client with mock backup service."""
    app.state.backup_service = mock_backup_service
    # Mock scheduler to avoid starting it
    app.state.scheduler = MagicMock()
    client = TestClient(app, raise_server_exceptions=False)
    yield client


class TestBackupAPIListBackups:
    """Tests for GET /api/backup/ endpoint."""

    def test_list_backups_empty(self, client_with_backup: TestClient) -> None:
        """Should return empty list when no backups exist."""
        response = client_with_backup.get("/api/backup/")
        assert response.status_code == 200
        data = response.json()
        assert data["backups"] == []
        assert data["total_count"] == 0

    def test_list_backups_with_backups(
        self, client_with_backup: TestClient, mock_backup_service: BackupService
    ) -> None:
        """Should return list of backups."""
        # Create a backup first
        mock_backup_service.create_backup()

        response = client_with_backup.get("/api/backup/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert len(data["backups"]) == 1
        assert data["backups"][0]["filename"].startswith("tools_")


class TestBackupAPICreateBackup:
    """Tests for POST /api/backup/ endpoint."""

    def test_create_backup_success(self, client_with_backup: TestClient) -> None:
        """Should create backup successfully."""
        response = client_with_backup.post("/api/backup/")
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Backup created successfully"
        assert data["backup"]["filename"].startswith("tools_")
        assert data["backup"]["size_bytes"] > 0


class TestBackupAPIRestoreBackup:
    """Tests for POST /api/backup/restore/{filename} endpoint."""

    def test_restore_backup_success(self, client_with_backup: TestClient, mock_backup_service: BackupService) -> None:
        """Should restore backup successfully."""
        # Create a backup first
        backup = mock_backup_service.create_backup()

        # Mock engine.dispose to avoid issues with test database
        with patch("html_tool_manager.core.db.engine"):
            response = client_with_backup.post(f"/api/backup/restore/{backup.filename}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["restored_from"] == backup.filename

    def test_restore_backup_not_found(self, client_with_backup: TestClient) -> None:
        """Should return 404 for non-existent backup."""
        response = client_with_backup.post("/api/backup/restore/tools_20250101_000000.db")
        assert response.status_code == 404

    def test_restore_backup_invalid_filename(self, client_with_backup: TestClient) -> None:
        """Should return 400 for invalid filename."""
        response = client_with_backup.post("/api/backup/restore/invalid.db")
        assert response.status_code == 400

    def test_restore_backup_invalid_pattern(self, client_with_backup: TestClient) -> None:
        """Should return 400 for filename not matching pattern."""
        # This tests the service-level validation (pattern check)
        response = client_with_backup.post("/api/backup/restore/malicious_file.db")
        assert response.status_code == 400


class TestBackupAPIDeleteBackup:
    """Tests for DELETE /api/backup/{filename} endpoint."""

    def test_delete_backup_success(self, client_with_backup: TestClient, mock_backup_service: BackupService) -> None:
        """Should delete backup successfully."""
        # Create a backup first
        backup = mock_backup_service.create_backup()

        response = client_with_backup.delete(f"/api/backup/{backup.filename}")
        assert response.status_code == 204

        # Verify backup is deleted
        backups = mock_backup_service.list_backups()
        assert len(backups) == 0

    def test_delete_backup_not_found(self, client_with_backup: TestClient) -> None:
        """Should return 404 for non-existent backup."""
        response = client_with_backup.delete("/api/backup/tools_20250101_000000.db")
        assert response.status_code == 404

    def test_delete_backup_invalid_filename(self, client_with_backup: TestClient) -> None:
        """Should return 400 for invalid filename."""
        response = client_with_backup.delete("/api/backup/invalid.db")
        assert response.status_code == 400

    def test_delete_backup_invalid_pattern(self, client_with_backup: TestClient) -> None:
        """Should return 400 for filename not matching pattern."""
        # This tests the service-level validation (pattern check)
        response = client_with_backup.delete("/api/backup/malicious_file.db")
        assert response.status_code == 400
