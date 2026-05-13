"""Enemy dataclass and intent system."""

from dataclasses import dataclass, field
from enum import Enum


class IntentType(Enum):
    ATTACK = "attack"
    DEFEND = "defend"
    SKILL = "skill"
    SPECIAL = "special"


@dataclass
class Intent:
    """An enemy's declared intent for the turn."""
    type: IntentType
    value: int = 0  # damage amount, block amount, etc.
    description_key: str = ""
    status: str = ""  # status to apply
    status_value: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Intent":
        return cls(
            type=IntentType(d.get("type", "attack")),
            value=d.get("value", 0),
            description_key=d.get("description_key", ""),
            status=d.get("status", ""),
            status_value=d.get("status_value", 0),
        )


@dataclass
class AIBehavior:
    """A behavior pattern for enemy AI."""
    pattern: list  # list of intent dicts (cycled through)
    pattern_type: str = "cycle"  # cycle, random, conditional
    condition: str = ""  # for conditional patterns (e.g., "hp_below_50")
    condition_value: int = 0
    phase: int = 1  # which phase this pattern belongs to

    @classmethod
    def from_dict(cls, d: dict) -> "AIBehavior":
        return cls(
            pattern=[Intent.from_dict(i) if isinstance(i, dict) else i for i in d.get("pattern", [])],
            pattern_type=d.get("pattern_type", "cycle"),
            condition=d.get("condition", ""),
            condition_value=d.get("condition_value", 0),
            phase=d.get("phase", 1),
        )


@dataclass
class Enemy:
    """An enemy in the game."""
    id: str
    name_key: str
    desc_key: str
    max_hp: int
    base_damage: int = 0
    floor: int = 1
    enemy_type: str = "normal"  # normal, elite, boss
    behaviors: list = field(default_factory=list)  # list of AIBehavior
    ascii_art: str = ""  # ASCII art representation
    keywords: list = field(default_factory=list)
    rewards: dict = field(default_factory=dict)  # {gold: int, card_chance: float, relic_chance: float}

    def get_behavior(self, phase: int = 1) -> AIBehavior:
        """Get the AI behavior for the current phase."""
        for b in self.behaviors:
            if isinstance(b, dict):
                b = AIBehavior.from_dict(b)
            if b.phase == phase:
                return b
        if self.behaviors:
            b = self.behaviors[0]
            return AIBehavior.from_dict(b) if isinstance(b, dict) else b
        return AIBehavior(pattern=[])

    @classmethod
    def from_dict(cls, d: dict) -> "Enemy":
        return cls(
            id=d["id"],
            name_key=d.get("name_key", f"enemy.{d['id']}"),
            desc_key=d.get("desc_key", f"enemy.{d['id']}.desc"),
            max_hp=d.get("max_hp", 20),
            base_damage=d.get("base_damage", 5),
            floor=d.get("floor", 1),
            enemy_type=d.get("enemy_type", "normal"),
            behaviors=[AIBehavior.from_dict(b) if isinstance(b, dict) else b for b in d.get("behaviors", [])],
            ascii_art=d.get("ascii_art", ""),
            keywords=d.get("keywords", []),
            rewards=d.get("rewards", {"gold": 10, "card_chance": 0.5, "relic_chance": 0.1}),
        )
