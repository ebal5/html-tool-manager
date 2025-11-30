"""Fixtures for E2E tests."""

import os
import subprocess
import time
from collections.abc import Generator

import pytest
from playwright.sync_api import Page


@pytest.fixture(scope="session")
def live_server() -> Generator[str, None, None]:
    """Start a test server for E2E tests.

    Yields:
        Base URL of the test server

    """
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "html_tool_manager.main:app", "--port", "8888"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(2)

    yield "http://localhost:8888"

    process.terminate()
    process.wait()


@pytest.fixture
def test_page(page: Page, live_server: str) -> Page:
    """Navigate to the test server and return the page.

    Args:
        page: Playwright page object
        live_server: Base URL of the test server

    Returns:
        Page object after navigating to the server

    """
    page.goto(live_server)
    return page
