"""HP Bar widget renderer."""

from abyssal.ui.colors import hp_color, BLOCK_BLUE


def render_hp_bar(current: int, maximum: int, width: int = 20, show_text: bool = True) -> str:
    """Render an HP bar: ████░░░░ style."""
    if maximum <= 0:
        return "[DEAD]"

    pct = max(0, min(1.0, current / maximum))
    filled = int(width * pct)
    empty = width - filled

    bar = "█" * filled + "░" * empty

    if show_text:
        return f"HP: {bar} {current}/{maximum}"
    return bar


def render_block(block: int) -> str:
    """Render block display."""
    if block <= 0:
        return ""
    return f"🛡 {block}"


def render_status_bar(statuses: dict, lang: str = "en") -> str:
    """Render active status effects as icons with stack counts."""
    from abyssal.i18n import t

    icons = {
        "vulnerable": ("💔", "red"),
        "weak": ("💜", "magenta"),
        "poison": ("☠", "green"),
        "charge": ("⚡", "yellow"),
        "dodge": ("💨", "cyan"),
        "regen": ("💚", "green"),
        "thorns": ("🌿", "yellow"),
        "freeze": ("❄", "blue"),
        "bloodrage": ("🩸", "red"),
        "attack": ("⚔", "red"),
        "defense": ("🛡", "blue"),
        "gale": ("🌀", "cyan"),
    }

    parts = []
    for name, status in statuses.items():
        if status.stacks <= 0:
            continue
        icon, _ = icons.get(name, ("?", ""))
        label = t(f"kw.{name}", lang) if t(f"kw.{name}", lang) != f"kw.{name}" else name
        parts.append(f"{icon}{label}:{status.stacks}")

    return " ".join(parts) if parts else ""
