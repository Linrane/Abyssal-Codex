"""JSON data loader with caching and validation."""

import json
import os
from pathlib import Path
from typing import Optional

from abyssal.data.cards import Card
from abyssal.data.enemies import Enemy
from abyssal.data.events import Event
from abyssal.data.heroes import Hero
from abyssal.data.relics import Relic


DATA_ROOT = Path(__file__).parent.parent.parent / "data"

# In-memory caches
_cache: dict = {}


def _load_json(path: str) -> dict:
    """Load a JSON file with caching."""
    if path in _cache:
        return _cache[path]
    full_path = DATA_ROOT / path
    if not full_path.exists():
        raise FileNotFoundError(f"Data file not found: {full_path}")
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _cache[path] = data
    return data


def _save_json(path: str, data: dict) -> None:
    """Save data to a JSON file."""
    full_path = DATA_ROOT / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_cards() -> dict[str, Card]:
    """Load all card definitions and return a dict keyed by card id."""
    cards = {}
    cards_dir = DATA_ROOT / "cards"
    if not cards_dir.exists():
        return cards
    for fname in cards_dir.glob("*.json"):
        data = _load_json(f"cards/{fname.name}")
        for card_data in data.get("cards", []):
            card = Card.from_dict(card_data)
            cards[card.id] = card
    return cards


def load_enemies() -> dict[str, Enemy]:
    """Load all enemy definitions."""
    enemies = {}
    enemies_dir = DATA_ROOT / "enemies"
    if not enemies_dir.exists():
        return enemies
    for fname in enemies_dir.glob("*.json"):
        data = _load_json(f"enemies/{fname.name}")
        for enemy_data in data.get("enemies", []):
            enemy = Enemy.from_dict(enemy_data)
            enemies[enemy.id] = enemy
    return enemies


def load_relics() -> dict[str, Relic]:
    """Load all relic definitions."""
    relics = {}
    relics_dir = DATA_ROOT / "relics"
    if not relics_dir.exists():
        return relics
    for fname in relics_dir.glob("*.json"):
        data = _load_json(f"relics/{fname.name}")
        for relic_data in data.get("relics", []):
            relic = Relic.from_dict(relic_data)
            relics[relic.id] = relic
    return relics


def load_heroes() -> dict[str, Hero]:
    """Load all hero definitions."""
    data = _load_json("heroes.json")
    heroes = {}
    for hero_data in data.get("heroes", []):
        hero = Hero.from_dict(hero_data)
        heroes[hero.id] = hero
    return heroes


def load_events() -> dict[str, Event]:
    """Load all event definitions."""
    events = {}
    events_dir = DATA_ROOT / "events"
    if not events_dir.exists():
        return events
    for fname in events_dir.glob("*.json"):
        data = _load_json(f"events/{fname.name}")
        for event_data in data.get("events", []):
            event = Event.from_dict(event_data)
            events[event.id] = event
    return events


def load_floors() -> dict:
    """Load floor definitions."""
    return _load_json("floors.json")


def load_meta() -> dict:
    """Load meta-progression data (unlocks, achievements, memory)."""
    meta_path = DATA_ROOT / ".." / "saves" / "meta.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"abyssal_memory": 0, "unlocked_cards": [], "unlocked_relics": [], "unlocked_heroes": ["knight", "weaver"], "achievements": [], "stats": {}}


def save_meta(data: dict) -> None:
    """Save meta-progression data."""
    meta_dir = DATA_ROOT / ".." / "saves"
    meta_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_dir / "meta.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear_cache() -> None:
    """Clear the data cache (useful for testing)."""
    _cache.clear()
