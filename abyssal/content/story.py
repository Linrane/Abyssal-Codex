"""Story flag tracker for narrative system."""


class StoryTracker:
    """Tracks story flags and choices during a run."""

    def __init__(self):
        self.flags: set[str] = set()
        self.choices: dict[str, str] = {}
        self.companions: list[str] = []
        self.boss_encounters: dict[str, bool] = {}

    def set_flag(self, flag: str) -> None:
        self.flags.add(flag)

    def has_flag(self, flag: str) -> bool:
        return flag in self.flags

    def remove_flag(self, flag: str) -> None:
        self.flags.discard(flag)

    def record_choice(self, event_id: str, choice: str) -> None:
        self.choices[event_id] = choice

    def get_choice(self, event_id: str) -> str:
        return self.choices.get(event_id, "")

    def add_companion(self, companion_id: str) -> None:
        if companion_id not in self.companions:
            self.companions.append(companion_id)

    def has_companion(self, companion_id: str) -> bool:
        return companion_id in self.companions

    def meet_boss(self, boss_id: str) -> None:
        self.boss_encounters[boss_id] = True

    def get_ending(self) -> str:
        """Determine which ending the player qualifies for."""
        if self.has_flag("freed_twelve_souls"):
            return "liberation"
        elif self.has_flag("defeated_old_god"):
            return "deicide"
        elif self.has_flag("consumed_abyss"):
            return "consumption"
        elif self.has_flag("resigned_power"):
            return "resignation"
        else:
            return "reseal"

    def to_dict(self) -> dict:
        return {
            "flags": list(self.flags),
            "choices": self.choices,
            "companions": self.companions,
            "boss_encounters": self.boss_encounters,
        }

    def from_dict(self, data: dict) -> None:
        self.flags = set(data.get("flags", []))
        self.choices = data.get("choices", {})
        self.companions = data.get("companions", [])
        self.boss_encounters = data.get("boss_encounters", {})
