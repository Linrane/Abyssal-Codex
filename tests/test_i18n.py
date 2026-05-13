"""Tests for i18n system."""

import pytest
from abyssal.i18n import t


def test_zh_strings():
    assert t("game.title", "zh") == "深渊牌匣"
    assert t("menu.new_game", "zh") == "新游戏"
    assert t("card.strike", "zh") == "打击"


def test_en_strings():
    assert t("game.title", "en") == "Abyssal Codex"
    assert t("menu.new_game", "en") == "New Game"
    assert t("card.strike", "en") == "Strike"


def test_fallback_to_zh():
    assert t("nonexistent_key", "en") == "nonexistent_key"
    assert t("game.title", "fr") == "深渊牌匣"


def test_all_zh_keys_have_en():
    from abyssal.i18n.zh import ZH
    from abyssal.i18n.en import EN
    missing = []
    for key in ZH:
        if key not in EN:
            missing.append(key)
    assert not missing, f"Missing EN keys: {missing}"


def test_all_en_keys_have_zh():
    from abyssal.i18n.zh import ZH
    from abyssal.i18n.en import EN
    missing = []
    for key in EN:
        if key not in ZH:
            missing.append(key)
    assert not missing, f"Missing ZH keys: {missing}"


def test_card_name_keys():
    card_keys = ["card.strike", "card.defend", "card.heavy_blow", "card.poison_blade"]
    for key in card_keys:
        assert t(key, "zh") != key, f"Missing ZH: {key}"
        assert t(key, "en") != key, f"Missing EN: {key}"
