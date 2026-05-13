"""Enemy intent icon display."""

from abyssal.data.enemies import Intent, IntentType


def render_intent(intent: Intent, lang: str = "en") -> str:
    """Render an enemy's intent as a single line."""
    from abyssal.i18n import t

    icons = {
        "attack": "⚔️",
        "defend": "🛡️",
        "skill": "💀",
        "special": "❓",
    }

    icon = icons.get(intent.type.value, "?")
    label = t(f"intent.{intent.type.value}", lang)

    if intent.type == IntentType.ATTACK:
        return f"{icon} {label}: {intent.value}"
    elif intent.type == IntentType.DEFEND:
        return f"{icon} {label}: {intent.value}"
    elif intent.type == IntentType.SKILL:
        st = t(f"kw.{intent.status}", lang)
        return f"{icon} {label}: {st} x{intent.status_value}"
    elif intent.type == IntentType.SPECIAL:
        st = t(f"kw.{intent.status}", lang)
        return f"{icon} {label}: {st} x{intent.status_value}"

    return f"{icon} ???"
