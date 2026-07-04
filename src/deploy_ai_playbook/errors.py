"""Common exception hierarchy.

Adopters who use the package programmatically (`from deploy_ai_playbook
import ...`) can catch every playbook-raised error with a single
`except AIPlaybookError`. Each module's existing concrete error class
subclasses this base, preserving the domain-specific parent (`ValueError`,
`RuntimeError`) so existing call-sites that catch those still work.

This module is at the foundation layer: it imports nothing from the
package and is safe to import from anywhere.
"""

from __future__ import annotations


class AIPlaybookError(Exception):
    """Base class for all errors raised by `deploy_ai_playbook`.

    Subclasses retain their domain-specific built-in parents (e.g.
    `UnknownAgentError(ValueError, AIPlaybookError)`) so that callers who
    catch `ValueError` continue to work; new callers can opt into the
    narrower `AIPlaybookError` for tooling and library use.
    """
