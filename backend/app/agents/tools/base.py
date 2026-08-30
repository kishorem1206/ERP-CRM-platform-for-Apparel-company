from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    data: Any = None
    error: str | None = None
    requires_confirmation: bool = False
    confirmation_summary: str | None = None
    audit_action: str | None = None


def permission_denied(permission: str) -> ToolResult:
    return ToolResult(success=False, error=f"Permission denied. Required: {permission}")


def rule_violation(reason: str) -> ToolResult:
    return ToolResult(success=False, error=reason)
