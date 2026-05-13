"""Relic dataclass."""

from dataclasses import dataclass, field
from enum import Enum


class RelicTier(Enum):
    COMMON = "common"
    BOSS = "boss"
    CURSE = "curse"
    LEGENDARY = "legendary"
    CLASS_SPECIFIC = "class"


@dataclass
class Relic:
    """A relic (permanent passive item)."""
    id: str
    name_key: str
    desc_key: str
    tier: RelicTier = RelicTier.COMMON
    character_class: str = "neutral"
    # Effect triggers
    on_combat_start: dict = field(default_factory=dict)  # {effect_type, value}
    on_turn_start: dict = field(default_factory=dict)
    on_turn_end: dict = field(default_factory=dict)
    on_damage_taken: dict = field(default_factory=dict)
    on_damage_dealt: dict = field(default_factory=dict)
    on_kill: dict = field(default_factory=dict)
    on_death: dict = field(default_factory=dict)
    on_card_played: dict = field(default_factory=dict)
    on_skip_reward: dict = field(default_factory=dict)
    passive: dict = field(default_factory=dict)  # {stat: value} e.g., {"max_energy": 1, "max_hp": -5}
    story_flags: list = field(default_factory=list)
    charges: int = 0  # For relics with limited uses per combat
    max_charges: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Relic":
        return cls(
            id=d["id"],
            name_key=d.get("name_key", f"relic.{d['id']}"),
            desc_key=d.get("desc_key", f"relic.{d['id']}.desc"),
            tier=RelicTier(d.get("tier", "common")),
            character_class=d.get("character_class", "neutral"),
            on_combat_start=d.get("on_combat_start", {}),
            on_turn_start=d.get("on_turn_start", {}),
            on_turn_end=d.get("on_turn_end", {}),
            on_damage_taken=d.get("on_damage_taken", {}),
            on_damage_dealt=d.get("on_damage_dealt", {}),
            on_kill=d.get("on_kill", {}),
            on_death=d.get("on_death", {}),
            on_card_played=d.get("on_card_played", {}),
            on_skip_reward=d.get("on_skip_reward", {}),
            passive=d.get("passive", {}),
            story_flags=d.get("story_flags", []),
            charges=d.get("charges", 0),
            max_charges=d.get("max_charges", 0),
        )
