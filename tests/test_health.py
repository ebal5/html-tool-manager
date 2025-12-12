"""Tests for the health check endpoint."""

from fastapi.testclient import TestClient

from html_tool_manager.main import app

client = TestClient(app)


def test_health_check_returns_200() -> None:
    """Test that health check endpoint returns 200 when healthy."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_response_structure() -> None:
    """Test that health check response has correct structure."""
    response = client.get("/health")
    data = response.json()

    assert "status" in data
    assert "components" in data
    assert "database" in data["components"]


def test_health_check_database_healthy() -> None:
    """Test that database component is healthy."""
    response = client.get("/health")
    data = response.json()

    assert data["status"] == "healthy"
    assert data["components"]["database"] == "healthy"
