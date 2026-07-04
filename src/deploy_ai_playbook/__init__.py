"""Deploy ai-playbook agents to Claude, Copilot, Cursor, or Kiro."""

from importlib.metadata import PackageNotFoundError, version

from deploy_ai_playbook.errors import AIPlaybookError

try:
    __version__ = version("ai-playbook")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = ["AIPlaybookError", "__version__"]
