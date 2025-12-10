"""Fixtures for E2E tests."""

import os
import socket
import subprocess
import time
from collections.abc import Generator

import pytest
import requests
from playwright.sync_api import Page


def _find_free_port() -> int:
    """Find a free port to use for the test server."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 10.0) -> bool:
    """Wait for the server to become available.

    Args:
        url: The URL to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if server is available, False if timeout reached

    """
    import sys

    start_time = time.time()
    last_error = None
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException as e:
            last_error = e
        time.sleep(0.1)

    # Log the last error for debugging
    if last_error:
        print(f"Server health check failed: {last_error}", file=sys.stderr)
    return False


@pytest.fixture(scope="session")
def live_server() -> Generator[str, None, None]:
    """Start a test server for E2E tests.

    Note:
        This fixture uses session scope for performance. Tests are isolated
        via the clean_database fixture which cleans data before/after each test.
        This works because pytest runs tests sequentially by default.
        If parallel execution (pytest-xdist) is needed, consider using
        scope="function" or isolated database files per worker.

    Yields:
        Base URL of the test server

    Raises:
        RuntimeError: If the server fails to start

    """
    port = _find_free_port()
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"

    process = subprocess.Popen(
        ["uv", "run", "uvicorn", "html_tool_manager.main:app", "--port", str(port)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    base_url = f"http://localhost:{port}"

    # Wait for server to start with health check
    if not _wait_for_server(base_url):
        # Server failed to start, get error output
        process.terminate()
        try:
            _, stderr = process.communicate(timeout=5)
            error_msg = stderr.decode() if stderr else "Unknown error"
        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "Process did not terminate"
        raise RuntimeError(f"Failed to start test server: {error_msg}")

    yield base_url

    # Cleanup with proper timeout
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)

    # Close pipes to prevent resource leaks
    if process.stdout:
        process.stdout.close()
    if process.stderr:
        process.stderr.close()


@pytest.fixture
def test_page(page: Page, live_server: str, clean_database: None) -> Page:
    """Navigate to the test server and return the page.

    Args:
        page: Playwright page object
        live_server: Base URL of the test server
        clean_database: Fixture to ensure database is clean

    Returns:
        Page object after navigating to the server

    """
    page.goto(live_server)
    return page


@pytest.fixture
def clean_database(live_server: str) -> Generator[None, None, None]:
    """Clean up the database before and after each test.

    Args:
        live_server: Base URL of the test server

    Yields:
        None

    """
    # Clean before test
    _delete_all_tools(live_server)

    yield

    # Clean after test
    _delete_all_tools(live_server)


def _delete_all_tools(base_url: str) -> None:
    """Delete all tools from the database via API.

    Args:
        base_url: Base URL of the test server

    """
    try:
        response = requests.get(f"{base_url}/api/tools/", timeout=5)
        if response.status_code == 200:
            tools = response.json()
            for tool in tools:
                requests.delete(f"{base_url}/api/tools/{tool['id']}", timeout=5)
    except requests.exceptions.RequestException:
        pass
