"""Card ASCII renderer — renders cards as 7×14 bordered boxes."""

from abyssal.data.cards import Card, CardType, Rarity
from abyssal.ui.colors import card_style, rarity_style, TEXT_BRIGHT, TEXT_DIM


def render_card(
    card: Card,
    lang: str = "en",
    highlighted: bool = False,
    playable: bool = True,
    width: int = 16,
    height: int = 7,
) -> str:
    """Render a single card as a multi-line ASCII string."""
    lines = []
    style = card_style(card.card_type.value)
    rstyle = rarity_style(card.rarity.value)

    cost = card.get_cost()
    cost_str = str(cost) + "⚡"

    # Top border
    if highlighted:
        lines.append(f"┏{'━' * (width - 2)}┓")
    else:
        lines.append(f"┌{'─' * (width - 2)}┐")

    # Line 1: Name + cost
    name = _get_name(card, lang)
    name = name[:width - len(cost_str) - 3]
    lines.append(f"│{name:<{width - len(cost_str) - 2}}{cost_str}│")

    # Line 2: Type + Rarity
    type_name = _get_type(card.card_type, lang)
    rarity_name = _get_rarity(card.rarity, lang)
    info = f"[{type_name}][{rarity_name}]"
    info = info[:width - 2]
    lines.append(f"│{info:<{width - 2}}│")

    # Line 3-4: Description
    desc = _get_desc(card, lang)
    if len(desc) > width - 2:
        # Split description
        part1 = desc[:width - 2]
        part2 = desc[width - 2:width * 2 - 4]
        lines.append(f"│{part1:<{width - 2}}│")
        lines.append(f"│{part2:<{width - 2}}│")
    else:
        lines.append(f"│{desc:<{width - 2}}│")
        lines.append(f"│{' ' * (width - 2)}│")

    # Line 5: Empty or keywords
    if card.keywords:
        kw = ",".join(card.keywords[:2])
        kw = kw[:width - 2]
        lines.append(f"│{kw:<{width - 2}}│")
    else:
        lines.append(f"│{' ' * (width - 2)}│")

    # Bottom border
    if highlighted:
        lines.append(f"┗{'━' * (width - 2)}┛")
    else:
        lines.append(f"└{'─' * (width - 2)}┘")

    if not playable:
        # Dim all lines
        pass

    return "\n".join(lines)


def render_hand(hand: list[Card], lang: str = "en", selected_index: int = -1) -> str:
    """Render all cards in hand horizontally."""
    if not hand:
        return "No cards in hand"

    card_strings = []
    for i, card in enumerate(hand):
        highlighted = (i == selected_index)
        card_str = render_card(card, lang, highlighted=highlighted)
        card_strings.append(card_str.split("\n"))

    # Combine horizontally
    height = len(card_strings[0]) if card_strings else 7
    result = []
    for line in range(height):
        row = ""
        for cs in card_strings:
            if line < len(cs):
                row += cs[line] + " "
        result.append(row)

    return "\n".join(result)


def _get_name(card: Card, lang: str) -> str:
    """Get localized card name."""
    from abyssal.i18n import t
    name = t(card.name_key, lang)
    if card.upgraded:
        name = t("misc.upgraded", lang) + name
    return name


def _get_type(card_type: CardType, lang: str) -> str:
    from abyssal.i18n import t
    key = f"card.type.{card_type.value}"
    return t(key, lang)


def _get_rarity(rarity: Rarity, lang: str) -> str:
    from abyssal.i18n import t
    key = f"rarity.{rarity.value}"
    return t(key, lang)


def _get_desc(card: Card, lang: str) -> str:
    """Get localized description with values filled in."""
    from abyssal.i18n import t
    desc_template = t(card.desc_key, lang)
    effects = card.get_effects()
    args = []
    for eff in effects:
        if eff.type in ("damage", "block", "heal", "apply_status"):
            args.append(str(eff.value))
        if eff.type in ("multi_hit",):
            args.extend([str(eff.value), str(eff.secondary_value)])
        if eff.secondary_value and eff.type not in ("multi_hit",):
            args.append(str(eff.secondary_value))
    try:
        return desc_template.format(*args)
    except (IndexError, KeyError):
        return desc_template
