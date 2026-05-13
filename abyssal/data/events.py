"""Event dataclass."""

from dataclasses import dataclass, field


@dataclass
class EventChoice:
    """A single choice within an event."""
    text_key: str
    effects: list = field(default_factory=list)  # list of effect dicts
    result_text_key: str = ""
    requires: dict = field(default_factory=dict)  # e.g., {"gold": 50, "card_id": "strike"}
    chance: float = 1.0  # Success chance (1.0 = guaranteed)
    fail_text_key: str = ""


@dataclass
class Event:
    """A map event/encounter."""
    id: str
    name_key: str
    description_key: str
    floor: int = 1
    event_type: str = "general"  # general, floor_theme, class_specific, story
    character_class: str = "any"
    ascii_art: str = ""
    choices: list = field(default_factory=list)
    story_flag_required: str = ""
    story_flag_set: str = ""  # Story flag to set after this event
    one_time: bool = True  # Can only appear once per run

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(
            id=d["id"],
            name_key=d.get("name_key", f"event.{d['id']}"),
            description_key=d.get("description_key", ""),
            floor=d.get("floor", 1),
            event_type=d.get("event_type", "general"),
            character_class=d.get("character_class", "any"),
            ascii_art=d.get("ascii_art", ""),
            choices=[EventChoice(
                text_key=c.get("text_key", ""),
                effects=c.get("effects", []),
                result_text_key=c.get("result_text_key", ""),
                requires=c.get("requires", {}),
                chance=c.get("chance", 1.0),
                fail_text_key=c.get("fail_text_key", ""),
            ) for c in d.get("choices", [])],
            story_flag_required=d.get("story_flag_required", ""),
            story_flag_set=d.get("story_flag_set", ""),
            one_time=d.get("one_time", True),
        )
