"""Output formatting utilities."""

from typing import Optional, Union


def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if not text:
        return ""
    text = str(text).replace('\n', ' ').strip()
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_tools_list(tools: list[str], max_display: int = 5) -> str:
    """Format a list of tools for display."""
    if not tools:
        return "(none)"
    if "*" in tools:
        return "All tools"
    if len(tools) <= max_display:
        return ", ".join(tools)
    return f"{', '.join(tools[:max_display])}... (+{len(tools) - max_display})"


def format_description(description: Union[str, list], max_length: int = 100) -> str:
    """Format a description, handling list or string input."""
    if isinstance(description, list):
        description = " ".join(str(d) for d in description)
    description = str(description).replace('\n', ' ').strip()
    return truncate(description, max_length)


def format_model(model: str) -> str:
    """Format model name for display."""
    model_names = {
        "haiku": "Haiku (fast, cost-effective)",
        "sonnet": "Sonnet (balanced)",
        "opus": "Opus (most capable)",
    }
    return model_names.get(model.lower(), model)


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def format_path(path, max_length: int = 40) -> str:
    """Format a path, shortening home directory and truncating if needed."""
    from pathlib import Path
    path_str = str(path)

    # Replace home directory with ~
    home = str(Path.home())
    if path_str.startswith(home):
        path_str = "~" + path_str[len(home):]

    return truncate(path_str, max_length)


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Return singular or plural form based on count."""
    if plural is None:
        plural = singular + "s"
    return singular if count == 1 else plural


def format_count(count: int, item_type: str, plural: Optional[str] = None) -> str:
    """Format a count with proper pluralization."""
    word = pluralize(count, item_type, plural)
    return f"{count} {word}"
