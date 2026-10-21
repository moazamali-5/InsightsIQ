"""Small formatting helpers shared across the app."""


def format_int(value: int) -> str:
    """Format an integer with thousands separators (e.g. 12,345)."""
    return f"{int(value):,}"


def format_pct(value: float, decimals: int = 1) -> str:
    """Format a number as a percentage string (e.g. 12.5%)."""
    return f"{value:.{decimals}f}%"


def format_bytes(num_bytes: float) -> str:
    """Format a byte count in a human-readable way (KB, MB, ...)."""
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"
