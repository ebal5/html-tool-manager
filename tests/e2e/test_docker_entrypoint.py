"""E2E tests for docker-entrypoint.sh.

These tests verify that the Docker entrypoint script correctly handles:
- Symlink detection for /data directory
- Permission fixes for root-owned /data
- Error handling when permission fixes fail
- Running the app as appuser

Note:
    These tests require Docker to be available and assume localhost networking
    works correctly (standard in GitHub Actions ubuntu-latest runners).
    Tests use Docker's automatic port allocation to avoid TOCTOU race conditions.

Environment Variables:
    E2E_DOCKER_IMAGE: Override the default Docker image tag for testing.
                      Default is "html-tool-manager:test".
    E2E_APP_STARTUP_TIMEOUT: Override the default app startup timeout in seconds.
                             Default is 30 seconds.

"""

import os
import subprocess
import time
import uuid
from collections.abc import Generator
from dataclasses import dataclass

import pytest
import requests

# Docker image tag used for testing (configurable via environment variable)
DOCKER_IMAGE = os.environ.get("E2E_DOCKER_IMAGE", "html-tool-manager:test")

# Test configuration constants (all floats for consistency)
APP_STARTUP_TIMEOUT = float(os.environ.get("E2E_APP_STARTUP_TIMEOUT", "30"))
DOCKER_COMMAND_TIMEOUT = 30.0  # seconds
DOCKER_BUILD_TIMEOUT = 300.0  # seconds (5 minutes for image build)
HTTP_REQUEST_TIMEOUT = 1.0  # seconds
POLLING_INTERVAL_SECONDS = 1.0  # seconds between HTTP health check polls


@dataclass
class RunningContainer:
    """Information about a running Docker container."""

    name: str
    host_port: int


def _run_docker(
    args: list[str],
    timeout: float = DOCKER_COMMAND_TIMEOUT,
    capture_output: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a docker command and return the result.

    Args:
        args: Arguments to pass to docker run
        timeout: Command timeout in seconds
        capture_output: Whether to capture stdout/stderr

    Returns:
        CompletedProcess with the command result

    """
    cmd = ["docker", "run", "--rm", *args]
    return subprocess.run(
        cmd,
        capture_output=capture_output,
        text=True,
        timeout=timeout,
    )


def _check_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _check_image_exists(image: str) -> bool:
    """Check if a Docker image exists."""
    try:
        result = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _generate_container_name(prefix: str = "test") -> str:
    """Generate a unique container name to avoid collisions.

    Args:
        prefix: Prefix for the container name

    Returns:
        Unique container name

    """
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _cleanup_container(container_name: str) -> None:
    """Stop and remove a Docker container.

    Args:
        container_name: Name of the container to clean up

    """
    subprocess.run(
        ["docker", "stop", container_name],
        capture_output=True,
        timeout=DOCKER_COMMAND_TIMEOUT,
    )
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        timeout=10,
    )


def _get_container_port(container_name: str, container_port: int = 80) -> int:
    """Get the host port mapped to a container port.

    Uses Docker's automatic port allocation to avoid TOCTOU race conditions.

    Args:
        container_name: Name of the container
        container_port: The container port to look up

    Returns:
        The host port number

    Raises:
        RuntimeError: If the port cannot be determined

    """
    result = subprocess.run(
        ["docker", "port", container_name, str(container_port)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get port: {result.stderr}")

    # Output format: "0.0.0.0:12345" or ":::12345"
    port_mapping = result.stdout.strip()
    # Extract port from the end after the last colon
    port_str = port_mapping.rsplit(":", 1)[-1]
    return int(port_str)


def _wait_for_app_ready(url: str, timeout: float = APP_STARTUP_TIMEOUT) -> bool:
    """Wait for the application to respond to HTTP requests.

    Args:
        url: The URL to check
        timeout: Maximum time to wait in seconds

    Returns:
        True if app is ready, False if timeout reached

    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(POLLING_INTERVAL_SECONDS)
    return False


# Skip all tests if Docker is not available
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not _check_docker_available(),
        reason="Docker is not available",
    ),
]


@pytest.fixture(scope="module")
def docker_image() -> str:
    """Ensure the Docker image is built for testing.

    Returns:
        The image tag to use for tests

    Raises:
        pytest.skip: If image doesn't exist and can't be built

    """
    if _check_image_exists(DOCKER_IMAGE):
        return DOCKER_IMAGE

    # Try to build the image
    result = subprocess.run(
        ["docker", "build", "-t", DOCKER_IMAGE, "."],
        capture_output=True,
        text=True,
        timeout=DOCKER_BUILD_TIMEOUT,
    )
    if result.returncode != 0:
        pytest.skip(f"Failed to build Docker image: {result.stderr}")

    return DOCKER_IMAGE


@pytest.fixture
def running_app_container(docker_image: str) -> Generator[RunningContainer, None, None]:
    """Start a container running the application and yield its info.

    This fixture manages the container lifecycle properly, ensuring cleanup
    even if tests crash.

    Yields:
        RunningContainer with name and host port

    """
    container_name = _generate_container_name("test-app")

    # Start the container with automatic port allocation
    # Using -p 80 (without host port) lets Docker assign an available port
    start_result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container_name,
            "-p",
            "80",  # Docker assigns random available host port
            docker_image,
        ],
        capture_output=True,
        text=True,
        timeout=DOCKER_COMMAND_TIMEOUT,
    )

    if start_result.returncode != 0:
        pytest.fail(f"Failed to start container: {start_result.stderr}")

    try:
        # Get the automatically assigned port
        host_port = _get_container_port(container_name, 80)

        # Wait for the application to be ready
        url = f"http://localhost:{host_port}/"
        if not _wait_for_app_ready(url):
            # Get logs for debugging
            logs = subprocess.run(
                ["docker", "logs", container_name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pytest.fail(
                f"Application did not become ready within {APP_STARTUP_TIMEOUT}s. Logs: {logs.stdout}{logs.stderr}"
            )

        yield RunningContainer(name=container_name, host_port=host_port)

    finally:
        _cleanup_container(container_name)


class TestDockerEntrypointSymlinkDetection:
    """Tests for symlink detection in docker-entrypoint.sh."""

    def test_rejects_symlink_data_directory(self, docker_image: str) -> None:
        """Entrypoint should reject /data when it's a symlink."""
        # Create a container with /data as a symlink to /tmp
        # We use a custom entrypoint to set up the symlink, then run the real entrypoint
        result = _run_docker(
            [
                "--entrypoint",
                "/bin/sh",
                docker_image,
                "-c",
                # Remove the /data directory and create a symlink to /tmp
                "rm -rf /data && ln -s /tmp /data && "
                # Then run the original entrypoint
                "exec /usr/local/bin/docker-entrypoint.sh echo test",
            ],
        )

        assert result.returncode == 1
        assert "symlink" in result.stderr.lower() or "symlink" in result.stdout.lower()


class TestDockerEntrypointPermissionFix:
    """Tests for permission fixes in docker-entrypoint.sh."""

    def test_fixes_root_owned_data_directory(self, docker_image: str) -> None:
        """Entrypoint should change ownership of /data when owned by root."""
        # Run a command that outputs the owner of /data after entrypoint runs
        # The entrypoint should have changed ownership to appuser (uid 1000)
        result = _run_docker(
            [
                docker_image,
                "stat",
                "-c",
                "%u",
                "/data",
            ],
        )

        assert result.returncode == 0
        # The owner should be appuser (uid 1000)
        owner_uid = result.stdout.strip()
        assert owner_uid == "1000", f"Expected owner uid 1000, got {owner_uid}"

    def test_data_directory_writable_by_appuser(self, docker_image: str) -> None:
        """After entrypoint, /data should be writable by appuser."""
        result = _run_docker(
            [
                docker_image,
                "touch",
                "/data/test_file",
            ],
        )

        assert result.returncode == 0

    def test_skips_chown_when_already_owned_by_appuser(self, docker_image: str) -> None:
        """Entrypoint should skip chown when /data is already owned by appuser (uid 1000).

        This tests the optimization in docker-entrypoint.sh that avoids
        unnecessary chown calls when permissions are already correct.
        """
        # When /data is pre-mounted with appuser ownership, chown should be skipped
        # We verify this by checking that the entrypoint succeeds and
        # the directory is still accessible
        result = _run_docker(
            [
                # Mount a tmpfs with appuser (uid 1000) ownership
                "--tmpfs",
                "/data:uid=1000,gid=1000",
                docker_image,
                "stat",
                "-c",
                "%u",
                "/data",
            ],
        )

        assert result.returncode == 0
        owner_uid = result.stdout.strip()
        assert owner_uid == "1000", f"Expected owner uid 1000, got {owner_uid}"

    def test_handles_empty_data_directory(self, docker_image: str) -> None:
        """Entrypoint should handle empty /data directory correctly."""
        # Verify that an empty /data directory works
        result = _run_docker(
            [
                docker_image,
                "ls",
                "-la",
                "/data",
            ],
        )

        assert result.returncode == 0


class TestDockerEntrypointPermissionFailure:
    """Tests for permission fix failure handling."""

    def test_exits_on_chown_failure(self, docker_image: str) -> None:
        """Entrypoint should exit with error when chown fails.

        This test simulates chown failure by using a read-only tmpfs mount
        for /data, which is portable across CI environments.
        """
        result = _run_docker(
            [
                # Mount the entire container filesystem as read-only
                "--read-only",
                # Need tmpfs for /tmp and other writable areas
                "--tmpfs",
                "/tmp:rw",
                "--tmpfs",
                "/run:rw",
                # Use a read-only tmpfs for /data to simulate chown failure
                # This is more portable than mounting host /tmp
                "--tmpfs",
                "/data:ro,uid=0,gid=0",
                docker_image,
                "echo",
                "should not reach here",
            ],
            # Shorter timeout: entrypoint should fail quickly on chown error
            timeout=10,
        )

        # The entrypoint should have failed
        assert result.returncode != 0
        # Check for the exact error message from docker-entrypoint.sh
        output = result.stdout + result.stderr
        assert "Error: Failed to change ownership of /data" in output


class TestDockerEntrypointNormalOperation:
    """Tests for normal operation of docker-entrypoint.sh."""

    def test_runs_command_as_appuser(self, docker_image: str) -> None:
        """Commands should run as appuser after entrypoint."""
        result = _run_docker(
            [
                docker_image,
                "id",
                "-un",
            ],
        )

        assert result.returncode == 0
        username = result.stdout.strip()
        assert username == "appuser", f"Expected appuser, got {username}"

    def test_runs_command_with_correct_uid(self, docker_image: str) -> None:
        """Commands should run with uid 1000 (appuser)."""
        result = _run_docker(
            [
                docker_image,
                "id",
                "-u",
            ],
        )

        assert result.returncode == 0
        uid = result.stdout.strip()
        assert uid == "1000", f"Expected uid 1000, got {uid}"

    def test_environment_variables_passed_through(self, docker_image: str) -> None:
        """Environment variables should be passed through to the command."""
        test_value = "test_env_value_12345"
        result = _run_docker(
            [
                "-e",
                f"TEST_ENV_VAR={test_value}",
                docker_image,
                "sh",
                "-c",
                "echo $TEST_ENV_VAR",
            ],
        )

        assert result.returncode == 0
        output = result.stdout.strip()
        assert output == test_value, f"Expected '{test_value}', got '{output}'"


class TestDockerEntrypointAppStartup:
    """Tests for application startup via docker-entrypoint.sh.

    Note:
        These tests use the running_app_container fixture which handles
        container lifecycle, port allocation, and startup verification.

    """

    def test_app_responds_to_http_requests(self, running_app_container: RunningContainer) -> None:
        """The application should start and respond to HTTP requests."""
        # The fixture already verified the app is responding
        # Double-check with an explicit request
        url = f"http://localhost:{running_app_container.host_port}/"
        response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
        assert response.status_code == 200

    def test_main_process_runs_as_appuser(self, running_app_container: RunningContainer) -> None:
        """The main process (PID 1) should run as appuser (uid 1000)."""
        # Verify the main process (PID 1) is running as appuser (uid 1000)
        # Use /proc/1/status since ps is not available in slim images
        exec_result = subprocess.run(
            [
                "docker",
                "exec",
                running_app_container.name,
                "sh",
                "-c",
                "grep '^Uid:' /proc/1/status | awk '{print $2}'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert exec_result.returncode == 0, f"Failed to get UID: {exec_result.stderr}"
        process_uid = exec_result.stdout.strip()
        assert process_uid == "1000", f"Expected PID 1 to run as uid 1000 (appuser), got {process_uid}"
