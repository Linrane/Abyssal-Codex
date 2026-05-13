"""Internationalization module for Abyssal Codex.

Supports Chinese (zh) and English (en) with fallback.
"""

from abyssal.i18n.en import EN
from abyssal.i18n.zh import ZH

STRINGS = {"zh": ZH, "en": EN}


def t(key: str, lang: str = "zh") -> str:
    """Look up a string by key, with fallback to Chinese."""
    strings = STRINGS.get(lang, ZH)
    return strings.get(key, ZH.get(key, key))
