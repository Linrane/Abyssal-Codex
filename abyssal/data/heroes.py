"""Hero dataclass and starting definitions."""

from dataclasses import dataclass, field


@dataclass
class Hero:
    """A playable hero class."""
    id: str
    name_key: str
    desc_key: str
    max_hp: int
    max_energy: int
    core_mechanic_key: str
    starting_deck: list  # list of card ids
    starting_relic: str = ""  # relic id
    unlocked: bool = True
    unlock_condition: str = ""
    ascii_art: str = ""
    keywords: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Hero":
        return cls(
            id=d["id"],
            name_key=d.get("name_key", f"hero.{d['id']}"),
            desc_key=d.get("desc_key", f"hero.{d['id']}.desc"),
            max_hp=d.get("max_hp", 70),
            max_energy=d.get("max_energy", 3),
            core_mechanic_key=d.get("core_mechanic_key", ""),
            starting_deck=d.get("starting_deck", []),
            starting_relic=d.get("starting_relic", ""),
            unlocked=d.get("unlocked", True),
            unlock_condition=d.get("unlock_condition", ""),
            ascii_art=d.get("ascii_art", ""),
            keywords=d.get("keywords", []),
        )
