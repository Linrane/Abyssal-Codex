"""Save/Load system using JSON files."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


SAVE_DIR = Path(__file__).parent.parent.parent / "saves"
META_FILE = SAVE_DIR / "meta.json"


class SaveManager:
    """Manages game save/load with 3 save slots."""

    def __init__(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        self.max_slots = 3

    def save(self, slot: int, data: dict) -> bool:
        """Save game state to a slot."""
        if slot < 1 or slot > self.max_slots:
            return False

        data["_save_time"] = datetime.now().isoformat()
        data["_slot"] = slot

        filepath = SAVE_DIR / f"slot_{slot}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True

    def load(self, slot: int) -> Optional[dict]:
        """Load game state from a slot."""
        filepath = SAVE_DIR / f"slot_{slot}.json"
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def delete(self, slot: int) -> bool:
        """Delete a save slot."""
        filepath = SAVE_DIR / f"slot_{slot}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def list_saves(self) -> list[dict]:
        """List all save slots with metadata."""
        saves = []
        for slot in range(1, self.max_slots + 1):
            data = self.load(slot)
            if data:
                saves.append({
                    "slot": slot,
                    "time": data.get("_save_time", "Unknown"),
                    "floor": data.get("current_floor", 1),
                    "hero_id": data.get("hero_id", "???"),
                    "hp": data.get("hp", 0),
                    "max_hp": data.get("max_hp", 0),
                })
        return saves

    def has_saves(self) -> bool:
        return len(self.list_saves()) > 0

    def load_meta(self) -> dict:
        """Load meta-progression data."""
        if META_FILE.exists():
            with open(META_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {
            "abyssal_memory": 0,
            "unlocked_cards": [],
            "unlocked_relics": [],
            "unlocked_heroes": ["knight", "weaver"],
            "achievements": [],
            "stats": {"total_runs": 0, "total_wins": 0, "total_bosses": 0, "total_cards": 0},
        }

    def save_meta(self, meta: dict) -> None:
        """Save meta-progression data."""
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        with open(META_FILE, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def add_memory(self, amount: int) -> int:
        """Add abyssal memory and return new total."""
        meta = self.load_meta()
        meta["abyssal_memory"] = meta.get("abyssal_memory", 0) + amount
        self.save_meta(meta)
        return meta["abyssal_memory"]

    def check_unlocks(self, meta: dict) -> list[str]:
        """Check for new unlocks based on stats. Returns list of unlocked ids."""
        new_unlocks = []
        stats = meta.get("stats", {})

        # Rune Sage: defeat 10 bosses
        if stats.get("total_bosses", 0) >= 10 and "sage" not in meta.get("unlocked_heroes", []):
            meta.setdefault("unlocked_heroes", []).append("sage")
            new_unlocks.append("sage")

        # Bloodbinder: use 20 power cards
        # Tracked elsewhere; placeholder
        if stats.get("total_powers_used", 0) >= 20 and "blood" not in meta.get("unlocked_heroes", []):
            meta.setdefault("unlocked_heroes", []).append("blood")
            new_unlocks.append("blood")

        return new_unlocks
