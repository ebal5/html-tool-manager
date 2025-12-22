"""Custom exceptions for HTML Tool Manager."""


class OptimisticLockError(Exception):
    """楽観的ロック競合時に発生する例外。

    ツールが別のユーザー/プロセスによって更新された場合に発生します。
    """

    def __init__(self, current_version: int, expected_version: int):
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__(f"Version conflict: expected {expected_version}, got {current_version}")
