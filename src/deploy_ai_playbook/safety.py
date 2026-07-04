"""Filesystem safety guards for writes under an adopter project root."""

from __future__ import annotations

import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path

from deploy_ai_playbook.errors import AIPlaybookError


class UnsafeDestinationError(RuntimeError, AIPlaybookError):
    """Raised when a deploy destination would write through a symlink."""


class WriteAccessError(OSError, AIPlaybookError):
    """Raised when the CLI cannot write to a deploy destination.

    Wraps the raw OSError (PermissionError, ReadOnlyError, "device full",
    "name too long", etc.) with a human-readable message that names the
    destination path and the underlying errno reason. The CLI surface
    translates this into a single-line Rich error and exits non-zero —
    much better first-time-user experience than a raw traceback.
    """


def assert_safe_destination(dst: Path, safe_root: Path | None) -> None:
    if safe_root is None:
        return
    lexical_root = safe_root.absolute()
    lexical_destination = dst.absolute()
    try:
        lexical_relative = lexical_destination.relative_to(lexical_root)
    except ValueError:
        pass
    else:
        current = lexical_root
        for part in lexical_relative.parts:
            current = current / part
            if current.is_symlink():
                raise UnsafeDestinationError(
                    f"Unsafe destination {dst}: refuses to write through symlink {current}"
                )

    root = safe_root.resolve()
    destination = dst.resolve(strict=False)
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise UnsafeDestinationError(
            f"Unsafe destination {dst}: path is outside target root {safe_root}"
        ) from exc


def preserve_broken_config(config_path: Path, safe_root: Path | None) -> Path:
    """Save a timestamped `.broken-<ts>` copy of an unusable config file.

    Shared by the malformed-JSON and non-object-JSON recovery paths (MCP and
    telemetry settings) so a user-edited file is never silently destroyed.
    """
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backup_path = config_path.with_suffix(config_path.suffix + f".broken-{timestamp}")
    write_text_safely(backup_path, config_path.read_text(encoding="utf-8"), safe_root)
    return backup_path


def write_text_safely(dst: Path, content: str, safe_root: Path | None) -> str:
    """Write `content` to `dst`, with safe-destination checks and graceful errors.

    Wraps mkdir/read/write in `OSError` handling so PermissionError,
    read-only-filesystem, and disk-full conditions surface as a typed
    `WriteAccessError` (a subclass of `OSError` and `AIPlaybookError`)
    rather than a Python traceback. Same behaviour for content unchanged
    (no-op return) so callers can rely on the status string.
    """
    assert_safe_destination(dst, safe_root)
    temp_path: Path | None = None
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and _text_matches(dst, content):
            return "[dim]unchanged[/dim]"
        temp_path = _temporary_sibling(dst)
        assert_safe_destination(temp_path, safe_root)
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(dst)
    except OSError as exc:
        _remove_temp_file(temp_path)
        raise WriteAccessError(
            f"Cannot write to {dst}: {exc.strerror or exc.__class__.__name__}"
        ) from exc
    return "[green]copied[/green]"


def write_bytes_safely(dst: Path, content: bytes, safe_root: Path | None) -> str:
    """Write bytes to `dst`, with the same destination guard and error shape as text writes."""
    assert_safe_destination(dst, safe_root)
    temp_path: Path | None = None
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() and dst.read_bytes() == content:
            return "[dim]unchanged[/dim]"
        temp_path = _temporary_sibling(dst)
        assert_safe_destination(temp_path, safe_root)
        temp_path.write_bytes(content)
        temp_path.replace(dst)
    except OSError as exc:
        _remove_temp_file(temp_path)
        raise WriteAccessError(
            f"Cannot write to {dst}: {exc.strerror or exc.__class__.__name__}"
        ) from exc
    return "[green]copied[/green]"


def _text_matches(path: Path, content: str) -> bool:
    try:
        return path.read_text(encoding="utf-8") == content
    except UnicodeDecodeError:
        return False


def _temporary_sibling(dst: Path) -> Path:
    with tempfile.NamedTemporaryFile(
        dir=dst.parent,
        prefix=f".{dst.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        return Path(temp_file.name)


def _remove_temp_file(temp_path: Path | None) -> None:
    if temp_path is None:
        return
    with suppress(OSError):
        temp_path.unlink(missing_ok=True)
