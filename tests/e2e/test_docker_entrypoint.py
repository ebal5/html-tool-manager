"""E2E tests for docker-entrypoint.sh.

These tests verify that the Docker entrypoint script correctly handles:
- Symlink detection for /data directory
- Permission fixes for root-owned /data
- Error handling when permission fixes fail
- Running the app as appuser

Note:
    These tests require Docker to be available and assume localhost networking
    works correctly (standard in GitHub Actions ubuntu-latest runners).
    Tests use dynamic port allocation to avoid conflicts.

"""

import subprocess
import time
import uuid

import pytest
import requests

from tests.e2e.conftest import _find_free_port

# Docker image tag used for testing
DOCKER_IMAGE = "html-tool-manager:test"

# Test configuration constants
APP_STARTUP_TIMEOUT = 20  # seconds
DOCKER_COMMAND_TIMEOUT = 30.0  # seconds
DOCKER_BUILD_TIMEOUT = 300.0  # seconds (5 minutes for image build)
HTTP_REQUEST_TIMEOUT = 0.5  # seconds
POLLING_INTERVAL_SECONDS = 1  # seconds between HTTP health check polls


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
        # Check for the specific error message from docker-entrypoint.sh
        output = result.stdout + result.stderr
        assert "Failed to change ownership" in output or "chown" in output.lower()


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


class TestDockerEntrypointAppStartup:
    """Tests for application startup via docker-entrypoint.sh.

    Note:
        These tests use localhost networking which works in standard Docker
        configurations including GitHub Actions ubuntu-latest runners.

    """

    def test_app_responds_to_http_requests(self, docker_image: str) -> None:
        """The application should start and respond to HTTP requests."""
        container_name = _generate_container_name("test-app-http")
        host_port = _find_free_port()

        # Start the container in the background
        start_result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-p",
                f"{host_port}:80",
                docker_image,
            ],
            capture_output=True,
            text=True,
            timeout=DOCKER_COMMAND_TIMEOUT,
        )

        try:
            assert start_result.returncode == 0, f"Failed to start: {start_result.stderr}"

            # Wait for the application to respond to HTTP requests
            app_ready = False
            url = f"http://localhost:{host_port}/"
            for _ in range(APP_STARTUP_TIMEOUT):
                try:
                    response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        app_ready = True
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(POLLING_INTERVAL_SECONDS)

            if not app_ready:
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

        finally:
            _cleanup_container(container_name)

    def test_main_process_runs_as_appuser(self, docker_image: str) -> None:
        """The main process (PID 1) should run as appuser (uid 1000)."""
        container_name = _generate_container_name("test-app-uid")
        host_port = _find_free_port()

        # Start the container in the background
        start_result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                container_name,
                "-p",
                f"{host_port}:80",
                docker_image,
            ],
            capture_output=True,
            text=True,
            timeout=DOCKER_COMMAND_TIMEOUT,
        )

        try:
            assert start_result.returncode == 0, f"Failed to start: {start_result.stderr}"

            # Wait for the application to start
            url = f"http://localhost:{host_port}/"
            for _ in range(APP_STARTUP_TIMEOUT):
                try:
                    response = requests.get(url, timeout=HTTP_REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(POLLING_INTERVAL_SECONDS)

            # Verify the main process (PID 1) is running as appuser (uid 1000)
            # Use /proc/1/status since ps is not available in slim images
            exec_result = subprocess.run(
                [
                    "docker",
                    "exec",
                    container_name,
                    "sh",
                    "-c",
                    "grep '^Uid:' /proc/1/status | awk '{print $2}'",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            process_uid = exec_result.stdout.strip()
            assert process_uid == "1000", f"Expected PID 1 to run as uid 1000 (appuser), got {process_uid}"

        finally:
            _cleanup_container(container_name)
