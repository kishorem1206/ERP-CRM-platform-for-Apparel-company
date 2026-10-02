import re

_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def render(text: str, context: dict[str, str]) -> str:
    """Substitute {{var}} placeholders from context. Unresolved vars are left
    as literal {{var}} rather than blanked, so missing data stays visible."""
    return _VAR_RE.sub(lambda m: context.get(m.group(1), m.group(0)), text)
