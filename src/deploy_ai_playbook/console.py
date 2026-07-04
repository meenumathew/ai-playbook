"""Shared Rich console instances for CLI presentation modules.

Errors and diagnostics go to stderr so CI/scripting can keep stdout clean
for `--json` payloads and piped output (Unix convention).
"""

from rich.console import Console

console = Console()
error_console = Console(stderr=True)
