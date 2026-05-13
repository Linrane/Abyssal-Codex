"""Card dataclass and related types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CardType(Enum):
    ATTACK = "attack"
    SKILL = "skill"
    POWER = "power"
    CURSE = "curse"
    LEGENDARY = "legendary"


class Rarity(Enum):
    COMMON = "common"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class TargetType(Enum):
    SINGLE_ENEMY = "single_enemy"
    ALL_ENEMIES = "all_enemies"
    SELF = "self"
    NONE = "none"


@dataclass
class CardEffect:
    """A single effect that a card applies."""
    type: str  # damage, block, apply_status, draw, gain_energy, heal, aoe, multi_hit
    value: int = 0
    status: str = ""  # Status keyword to apply
    duration: int = 0
    secondary_value: int = 0  # For effects with two numbers (e.g., damage + block)
    condition: str = ""  # Optional condition for conditional effects
    condition_value: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "CardEffect":
        return cls(
            type=d.get("type", ""),
            value=d.get("value", 0),
            status=d.get("status", ""),
            duration=d.get("duration", 0),
            secondary_value=d.get("secondary_value", 0),
            condition=d.get("condition", ""),
            condition_value=d.get("condition_value", 0),
        )


@dataclass
class Card:
    """A card in the game."""
    id: str
    name_key: str  # i18n key
    desc_key: str  # i18n key with {0}, {1} placeholders
    card_type: CardType
    rarity: Rarity
    cost: int
    target: TargetType = TargetType.SINGLE_ENEMY
    effects: list = field(default_factory=list)
    upgraded: bool = False
    upgraded_cost: int = 0  # 0 means not upgradable
    upgraded_effects: list = field(default_factory=list)
    character_class: str = "neutral"  # neutral or class id
    keywords: list = field(default_factory=list)  # list of keyword strings
    exhaust: bool = False
    innate: bool = False

    def get_cost(self) -> int:
        if self.upgraded and self.upgraded_cost:
            return self.upgraded_cost
        return self.cost

    def get_effects(self) -> list:
        if self.upgraded and self.upgraded_effects:
            return [CardEffect.from_dict(e) if isinstance(e, dict) else e for e in self.upgraded_effects]
        return [CardEffect.from_dict(e) if isinstance(e, dict) else e for e in self.effects]

    def __hash__(self):
        return hash(self.id + ("_up" if self.upgraded else ""))

    def __eq__(self, other):
        if not isinstance(other, Card):
            return False
        return self.id == other.id and self.upgraded == other.upgraded

    @classmethod
    def from_dict(cls, d: dict) -> "Card":
        return cls(
            id=d["id"],
            name_key=d.get("name_key", f"card.{d['id']}"),
            desc_key=d.get("desc_key", f"card.{d['id']}.desc"),
            card_type=CardType(d.get("card_type", "attack")),
            rarity=Rarity(d.get("rarity", "common")),
            cost=d.get("cost", 1),
            target=TargetType(d.get("target", "single_enemy")),
            effects=[CardEffect.from_dict(e) for e in d.get("effects", [])],
            upgraded=d.get("upgraded", False),
            upgraded_cost=d.get("upgraded_cost", 0),
            upgraded_effects=[CardEffect.from_dict(e) for e in d.get("upgraded_effects", [])],
            character_class=d.get("character_class", "neutral"),
            keywords=d.get("keywords", []),
            exhaust=d.get("exhaust", False),
            innate=d.get("innate", False),
        )
