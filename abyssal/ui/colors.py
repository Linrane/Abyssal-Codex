"""Color palette for Abyssal Codex terminal UI."""

from rich.style import Style
from rich.color import Color

# Primary card type colors
ATTACK_RED = Style(color=Color.from_hex("#FF4444"))
SKILL_BLUE = Style(color=Color.from_hex("#4488FF"))
POWER_GREEN = Style(color=Color.from_hex("#44FF44"))
CURSE_PURPLE = Style(color=Color.from_hex("#AA44FF"))
LEGENDARY_GOLD = Style(color=Color.from_hex("#FFAA00"))

# Rarity colors
RARITY_COMMON = Style(color=Color.from_hex("#AAAAAA"))
RARITY_RARE = Style(color=Color.from_hex("#4488FF"))
RARITY_EPIC = Style(color=Color.from_hex("#AA44FF"))
RARITY_LEGENDARY = Style(color=Color.from_hex("#FFAA00"))

# UI element colors
HP_RED = Style(color=Color.from_hex("#FF4444"))
HP_GREEN = Style(color=Color.from_hex("#44FF44"))
HP_YELLOW = Style(color=Color.from_hex("#FFCC00"))
BLOCK_BLUE = Style(color=Color.from_hex("#4488FF"))
ENERGY_YELLOW = Style(color=Color.from_hex("#FFAA00"))
GOLD_YELLOW = Style(color=Color.from_hex("#FFDD44"))

# Status colors
POISON_GREEN = Style(color=Color.from_hex("#44FF44"))
VULNERABLE_RED = Style(color=Color.from_hex("#FF6666"))
WEAK_PURPLE = Style(color=Color.from_hex("#9966CC"))
DODGE_CYAN = Style(color=Color.from_hex("#44DDDD"))
FREEZE_BLUE = Style(color=Color.from_hex("#88BBFF"))
THORNS_ORANGE = Style(color=Color.from_hex("#FF8844"))
CHARGE_YELLOW = Style(color=Color.from_hex("#FFCC00"))

# Background / UI chrome
BG_DARK = Style(bgcolor=Color.from_hex("#0D1117"))
PANEL_BORDER = Style(color=Color.from_hex("#30363D"))
TEXT_DIM = Style(color=Color.from_hex("#8B949E"))
TEXT_BRIGHT = Style(color=Color.from_hex("#E6EDF3"))
TEXT_HIGHLIGHT = Style(color=Color.from_hex("#FFAA00"))

# Map node colors
NODE_COMBAT = Style(color=Color.from_hex("#FF4444"))
NODE_ELITE = Style(color=Color.from_hex("#FF8844"))
NODE_SHOP = Style(color=Color.from_hex("#FFDD44"))
NODE_EVENT = Style(color=Color.from_hex("#44DDDD"))
NODE_REST = Style(color=Color.from_hex("#44FF44"))
NODE_BOSS = Style(color=Color.from_hex("#FF0044"))
NODE_START = Style(color=Color.from_hex("#4488FF"))


def card_style(card_type: str) -> Style:
    """Get the color style for a card type."""
    return {
        "attack": ATTACK_RED,
        "skill": SKILL_BLUE,
        "power": POWER_GREEN,
        "curse": CURSE_PURPLE,
        "legendary": LEGENDARY_GOLD,
    }.get(card_type, TEXT_BRIGHT)


def rarity_style(rarity: str) -> Style:
    """Get the color style for a rarity."""
    return {
        "common": RARITY_COMMON,
        "rare": RARITY_RARE,
        "epic": RARITY_EPIC,
        "legendary": RARITY_LEGENDARY,
    }.get(rarity, RARITY_COMMON)


def hp_color(hp: int, max_hp: int) -> Style:
    """Get color for HP bar based on percentage."""
    pct = hp / max_hp if max_hp > 0 else 0
    if pct > 0.6:
        return HP_GREEN
    elif pct > 0.3:
        return HP_YELLOW
    return HP_RED
