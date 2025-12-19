"""E2E tests for docker-entrypoint.sh.

These tests verify that the Docker entrypoint script correctly handles:
- Symlink detection for /data directory
- Permission fixes for root-owned /data
- Error handling when permission fixes fail
- Running the app as appuser
"""

import subprocess
import time

import pytest
import requests

# Docker image tag used for testing
DOCKER_IMAGE = "html-tool-manager:test"


def _run_docker(
    args: list[str],
    timeout: float = 30.0,
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
        timeout=300,
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

        This test uses a read-only mount for /data to simulate chown failure.
        """
        # Create a temporary directory and mount it as read-only
        # This will cause chown to fail
        result = _run_docker(
            [
                # Mount /data as read-only (using tmpfs with ro)
                "--read-only",
                # Need tmpfs for /tmp and other writable areas
                "--tmpfs",
                "/tmp:rw",
                "--tmpfs",
                "/run:rw",
                # Override /data with a read-only volume to force chown failure
                # We need to mount a volume owned by root
                "-v",
                "/tmp:/data:ro",
                docker_image,
                "echo",
                "should not reach here",
            ],
            timeout=10,
        )

        # The entrypoint should have failed
        assert result.returncode != 0
        # Check for error message about ownership change
        output = result.stdout + result.stderr
        assert "ownership" in output.lower() or "chown" in output.lower() or "read-only" in output.lower()


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

    def test_app_starts_successfully(self, docker_image: str) -> None:
        """The application should start successfully."""
        container_name = "test-entrypoint-app"
        host_port = 8888

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
            timeout=30,
        )

        try:
            assert start_result.returncode == 0, f"Failed to start: {start_result.stderr}"

            # Wait for the application to respond to HTTP requests
            app_ready = False
            url = f"http://localhost:{host_port}/"
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code == 200:
                        app_ready = True
                        break
                except requests.exceptions.RequestException:
                    pass
                time.sleep(1)

            if not app_ready:
                # Get logs for debugging
                logs = subprocess.run(
                    ["docker", "logs", container_name],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                pytest.fail(f"Application did not become ready within timeout. Logs: {logs.stdout}{logs.stderr}")

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
            # Cleanup: stop and remove the container
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=30,
            )
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=10,
            )
