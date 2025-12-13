"""Tests for the health check endpoint."""

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session


def test_health_check_returns_200(session: Session, client: TestClient) -> None:
    """Test that health check endpoint returns 200 when healthy."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_response_structure(session: Session, client: TestClient) -> None:
    """Test that health check response has correct structure."""
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]


def test_health_check_database_healthy(session: Session, client: TestClient) -> None:
    """Test that database component is healthy."""
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["components"]["database"] == "healthy"


def test_health_check_database_error_returns_503(session: Session, client: TestClient) -> None:
    """Test that health check returns 503 when database is unhealthy."""
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("Database connection failed", params=None, orig=None)

    with patch("html_tool_manager.main.engine", mock_engine):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["components"]["database"] == "unhealthy"
