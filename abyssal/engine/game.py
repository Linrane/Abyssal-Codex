"""Main game loop and state management."""

import random
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from abyssal.data.cards import Card, Rarity, CardType
from abyssal.data.enemies import Enemy
from abyssal.data.events import Event
from abyssal.data.heroes import Hero
from abyssal.data.loader import (
    load_cards,
    load_enemies,
    load_events,
    load_floors,
    load_heroes,
    load_relics,
)
from abyssal.data.relics import Relic


class RoomType(Enum):
    START = "start"
    COMBAT = "combat"
    ELITE = "elite"
    SHOP = "shop"
    EVENT = "event"
    REST = "rest"
    BOSS = "boss"


class RunPhase(Enum):
    MAP = "map"
    COMBAT = "combat"
    EVENT = "event"
    SHOP = "shop"
    REST = "rest"
    REWARD = "reward"
    GAME_OVER = "game_over"


@dataclass
class MapNode:
    """A single node on the floor map."""
    id: str
    room_type: RoomType
    row: int = 0
    col: int = 0
    connected_to: list[str] = field(default_factory=list)
    visited: bool = False
    available: bool = False


@dataclass
class FloorMap:
    """A floor map with nodes and connections."""
    floor_id: int
    nodes: dict[str, MapNode] = field(default_factory=dict)
    current_node: str = ""
    start_node: str = ""
    boss_node: str = ""


@dataclass
class RunState:
    """The state of a complete run."""
    hero: Hero
    hp: int
    max_hp: int
    max_energy: int
    deck: list[Card]
    relics: list[Relic]
    gold: int = 100
    current_floor: int = 1
    floor_map: Optional[FloorMap] = None
    phase: RunPhase = RunPhase.MAP
    story_flags: set = field(default_factory=set)
    encounters_completed: int = 0
    bosses_defeated: int = 0
    cards_collected: int = 0
    gold_total: int = 0
    events_seen: set = field(default_factory=set)
    remove_count: int = 0  # Track removal costs
    turn: int = 0
    lang: str = "zh"


class GameEngine:
    """Main game engine managing run progression."""

    def __init__(self, lang: str = "zh"):
        self.lang = lang
        self.state: Optional[RunState] = None
        self._all_cards: dict[str, Card] = {}
        self._all_enemies: dict[str, Enemy] = {}
        self._all_relics: dict[str, Relic] = {}
        self._all_events: dict[str, Event] = {}
        self._all_heroes: dict[str, Hero] = {}
        self._floors_data: dict = {}
        self._loaded = False

    def load_data(self) -> None:
        """Load all game data from JSON files."""
        if self._loaded:
            return
        self._all_cards = load_cards()
        self._all_enemies = load_enemies()
        self._all_relics = load_relics()
        self._all_events = load_events()
        self._all_heroes = load_heroes()
        self._floors_data = load_floors()
        self._loaded = True

    def get_unlocked_heroes(self) -> list[Hero]:
        """Get list of currently unlocked heroes."""
        self.load_data()
        return [h for h in self._all_heroes.values() if h.unlocked]

    def start_run(self, hero_id: str) -> RunState:
        """Start a new run with the given hero."""
        self.load_data()
        hero = self._all_heroes[hero_id]

        # Build starting deck
        deck = []
        for card_id in hero.starting_deck:
            if card_id in self._all_cards:
                deck.append(deepcopy(self._all_cards[card_id]))

        # Starting relic
        relics = []
        if hero.starting_relic and hero.starting_relic in self._all_relics:
            relics.append(deepcopy(self._all_relics[hero.starting_relic]))

        state = RunState(
            hero=deepcopy(hero),
            hp=hero.max_hp,
            max_hp=hero.max_hp,
            max_energy=hero.max_energy,
            deck=deck,
            relics=relics,
            lang=self.lang,
        )

        self.state = state
        self._generate_floor(1)
        return state

    def _generate_floor(self, floor_id: int) -> None:
        """Generate a floor map with guaranteed diverse node types."""
        floor_data = None
        for f in self._floors_data.get("floors", []):
            if f["id"] == floor_id:
                floor_data = f
                break

        if not floor_data:
            return

        num_rooms = random.randint(
            floor_data.get("rooms_min", 4),
            floor_data.get("rooms_max", 6),
        )
        num_rooms = min(num_rooms, 8)

        nodes = {}

        # Row 0: Start node
        nodes["start"] = MapNode(id="start", room_type=RoomType.START, row=0, col=2,
                                  available=True, visited=True)

        # Plan rows 1..num_rooms-1 (boss at num_rooms)
        # Guarantee: 1 event, 1 shop, 1 rest across the floor
        side_types = [RoomType.EVENT, RoomType.SHOP, RoomType.REST]
        random.shuffle(side_types)

        prev_nodes = ["start"]  # nodes from previous row that connect forward
        side_idx = 0

        for row in range(1, num_rooms):
            # Always place a combat node at this row
            cid = f"c{row}"
            nodes[cid] = MapNode(id=cid, room_type=RoomType.COMBAT, row=row,
                                  col=2, available=True)

            # Connect all previous nodes to this combat
            for pn in prev_nodes:
                if cid not in nodes[pn].connected_to:
                    nodes[pn].connected_to.append(cid)

            # Place a side node at this row
            new_prev = [cid]
            if side_idx < len(side_types):
                stype = side_types[side_idx]
                sid = f"s{row}"
                nodes[sid] = MapNode(id=sid, room_type=stype, row=row,
                                      col=4, available=True)
                for pn in prev_nodes:
                    if sid not in nodes[pn].connected_to:
                        nodes[pn].connected_to.append(sid)
                # Side node also connects forward to combat
                nodes[sid].connected_to.append(cid)
                new_prev.append(sid)
                side_idx += 1

            prev_nodes = new_prev

        # Boss row
        nodes["boss"] = MapNode(id="boss", room_type=RoomType.BOSS, row=num_rooms,
                                 col=2, available=False)
        for pn in prev_nodes:
            nodes[pn].connected_to.append("boss")

        floor_map = FloorMap(
            floor_id=floor_id,
            nodes=nodes,
            current_node="start",
            start_node="start",
            boss_node="boss",
        )

        self.state.floor_map = floor_map
        self.state.phase = RunPhase.MAP

    def get_available_nodes(self) -> list[str]:
        """Get nodes the player can move to."""
        if not self.state or not self.state.floor_map:
            return []
        current = self.state.floor_map.nodes.get(self.state.floor_map.current_node)
        if not current:
            return []
        available = []
        for nid in current.connected_to:
            if nid in self.state.floor_map.nodes:
                node = self.state.floor_map.nodes[nid]
                if not node.visited:
                    available.append(nid)
        return available

    def move_to_node(self, node_id: str) -> bool:
        """Move to a node on the map. Returns True if successful."""
        if not self.state or not self.state.floor_map:
            return False

        fm = self.state.floor_map
        if node_id not in fm.nodes:
            return False
        if node_id not in self.get_available_nodes():
            return False

        fm.current_node = node_id
        fm.nodes[node_id].visited = True

        node = fm.nodes[node_id]
        if node.room_type == RoomType.COMBAT:
            self.state.phase = RunPhase.COMBAT
        elif node.room_type == RoomType.ELITE:
            self.state.phase = RunPhase.COMBAT
        elif node.room_type == RoomType.SHOP:
            self.state.phase = RunPhase.SHOP
        elif node.room_type == RoomType.EVENT:
            self.state.phase = RunPhase.EVENT
        elif node.room_type == RoomType.REST:
            self.state.phase = RunPhase.REST
        elif node.room_type == RoomType.BOSS:
            self.state.phase = RunPhase.COMBAT

        return True

    def get_encounter_enemies(self) -> list[Enemy]:
        """Get enemies for the current room."""
        if not self.state:
            return []

        floor_data = None
        for f in self._floors_data.get("floors", []):
            if f["id"] == self.state.current_floor:
                floor_data = f
                break

        node = self.state.floor_map.nodes[self.state.floor_map.current_node]
        pool_key = "enemy_pool"
        if node.room_type == RoomType.ELITE:
            pool_key = "elite_pool"
        elif node.room_type == RoomType.BOSS:
            pool_key = "boss_pool"

        enemy_ids = floor_data.get(pool_key, [])
        enemies = []
        num_enemies = 1 if node.room_type != RoomType.ELITE else 2

        for _ in range(num_enemies):
            if enemy_ids:
                eid = random.choice(enemy_ids)
                if eid in self._all_enemies:
                    enemies.append(deepcopy(self._all_enemies[eid]))

        return enemies

    def get_floor_effect(self) -> dict:
        """Get the environmental effect for the current floor."""
        for f in self._floors_data.get("floors", []):
            if f["id"] == self.state.current_floor:
                return f.get("effect", {})
        return {}

    def get_random_event(self) -> Optional[Event]:
        """Get a random event appropriate for the current floor."""
        if not self.state:
            return None

        floor_data = None
        for f in self._floors_data.get("floors", []):
            if f["id"] == self.state.current_floor:
                floor_data = f
                break

        if not floor_data:
            return None

        event_pool = floor_data.get("event_pool", [])
        # Filter out seen events
        available = [eid for eid in event_pool if eid not in self.state.events_seen]
        if not available:
            available = event_pool

        if not available:
            return None

        eid = random.choice(available)
        self.state.events_seen.add(eid)
        if eid in self._all_events:
            return deepcopy(self._all_events[eid])
        return None

    def get_card_pool(self) -> list[Card]:
        """Get the card pool for reward generation (hero class + neutral)."""
        hero_class = self.state.hero.id
        pool = []
        for card in self._all_cards.values():
            if card.card_type == CardType.CURSE:
                continue
            # Already have 3+ copies of a common card? Skip
            if card.rarity == Rarity.COMMON:
                count = sum(1 for c in self.state.deck if c.id == card.id)
                if count >= 3:
                    continue
            if card.character_class in ("neutral", hero_class):
                pool.append(deepcopy(card))
        return pool

    def generate_card_rewards(self, count: int = 3) -> list[Card]:
        """Generate card reward choices."""
        pool = self.get_card_pool()
        if not pool:
            return []

        rewards = []
        # Rarity weights
        weights = {Rarity.COMMON: 50, Rarity.RARE: 30, Rarity.EPIC: 15, Rarity.LEGENDARY: 5}
        for _ in range(count):
            weighted_pool = []
            for card in pool:
                w = weights.get(card.rarity, 10)
                weighted_pool.extend([card] * w)
            if weighted_pool:
                choice = random.choice(weighted_pool)
                rewards.append(choice)
                # Don't offer duplicates
                pool = [c for c in pool if c.id != choice.id]

        return rewards

    def generate_relic_reward(self) -> Optional[Relic]:
        """Generate a random relic reward."""
        available = [r for r in self._all_relics.values() if r.tier.value in ("common",)]
        if not available:
            return None
        return deepcopy(random.choice(available))

    def generate_boss_relic(self) -> Optional[Relic]:
        """Generate a boss relic."""
        available = [r for r in self._all_relics.values() if r.tier.value in ("boss", "common")]
        if not available:
            return None
        return deepcopy(random.choice(available))

    def add_card_to_deck(self, card: Card) -> None:
        """Add a card to the player's deck."""
        self.state.deck.append(deepcopy(card))
        self.state.cards_collected += 1

    def remove_card_from_deck(self, card_index: int) -> bool:
        """Remove a card from the deck. Returns True if successful."""
        if 0 <= card_index < len(self.state.deck):
            self.state.deck.pop(card_index)
            self.state.remove_count += 1
            return True
        return False

    def get_remove_cost(self) -> int:
        """Get the cost to remove a card at the shop."""
        costs = [75, 125, 200, 300]
        idx = min(self.state.remove_count, len(costs) - 1)
        cost = costs[idx]
        # Lucky coin discount
        for relic in self.state.relics:
            if "shop_discount" in relic.passive:
                cost = int(cost * (1 - relic.passive["shop_discount"]))
        return cost

    def rest_heal(self) -> int:
        """Heal 30% HP at a rest site. Returns amount healed."""
        heal_amount = int(self.state.max_hp * 0.3)
        old_hp = self.state.hp
        self.state.hp = min(self.state.max_hp, self.state.hp + heal_amount)
        return self.state.hp - old_hp

    def rest_upgrade(self, card_index: int) -> bool:
        """Upgrade a card at a rest site. Returns True if successful."""
        if 0 <= card_index < len(self.state.deck):
            card = self.state.deck[card_index]
            if card.upgraded_cost > 0 or card.upgraded_effects:
                card.upgraded = True
                return True
        return False

    def add_gold(self, amount: int) -> None:
        """Add gold to the player's total."""
        self.state.gold += amount
        self.state.gold_total += amount

    def spend_gold(self, amount: int) -> bool:
        """Spend gold. Returns True if successful."""
        if self.state.gold >= amount:
            self.state.gold -= amount
            return True
        return False

    def complete_floor(self) -> bool:
        """Mark floor as complete. Returns True if game is won."""
        self.state.current_floor += 1
        if self.state.current_floor > 3:
            return True  # Game won!
        self._generate_floor(self.state.current_floor)
        return False  # Continue to next floor

    def determine_ending(self) -> str:
        """Determine which ending the player gets based on story flags."""
        if not self.state:
            return "reseal"

        flags = self.state.story_flags
        # Check endings in priority order
        if "defeated_old_god" in flags:
            return "deicide"
        if "freed_twelve_souls" in flags:
            return "liberation"
        if "consumed_abyss" in flags:
            return "consumption"
        if "accepted_void_mercy" in flags:
            return "resignation"
        return "reseal"

    def calculate_memory(self) -> int:
        """Calculate Abyssal Memory earned at end of run."""
        if not self.state:
            return 0
        memory = 0
        memory += self.state.current_floor * 10  # Up to 30 for floors reached
        memory += self.state.bosses_defeated * 15  # 15 per boss
        memory += self.state.encounters_completed * 3  # 3 per encounter
        return memory

    def check_achievements(self) -> list[str]:
        """Check which achievements were earned this run. Returns list of achievement IDs."""
        if not self.state:
            return []

        earned = []
        s = self.state

        # Floor clears
        if s.bosses_defeated >= 1:
            earned.append("floor1_clear")
        if s.bosses_defeated >= 2:
            earned.append("floor2_clear")
        if s.bosses_defeated >= 3:
            earned.append("floor3_clear")
            earned.append("first_win")

        # Class wins
        if s.bosses_defeated >= 3:
            if s.hero.id == "knight":
                earned.append("knight_win")
            elif s.hero.id == "weaver":
                earned.append("weaver_win")

        # Deck size
        if len(s.deck) >= 30:
            earned.append("huge_deck")
        if len(s.deck) <= 10 and s.bosses_defeated >= 3:
            earned.append("thin_deck")

        # Wealth
        if s.gold_total >= 500:
            earned.append("rich")

        # Relic count
        if len(s.relics) >= 10:
            earned.append("many_relics")

        # Ending achievements
        ending = self.determine_ending()
        if ending == "liberation":
            earned.append("liberation_end")
        elif ending == "deicide":
            earned.append("deicide_end")

        return earned

    def to_dict(self) -> dict:
        """Serialize run state to a dictionary for saving."""
        if not self.state:
            return {}

        return {
            "hero_id": self.state.hero.id,
            "hp": self.state.hp,
            "max_hp": self.state.max_hp,
            "max_energy": self.state.max_energy,
            "gold": self.state.gold,
            "current_floor": self.state.current_floor,
            "phase": self.state.phase.value,
            "deck": [{"id": c.id, "upgraded": c.upgraded} for c in self.state.deck],
            "relics": [r.id for r in self.state.relics],
            "story_flags": list(self.state.story_flags),
            "encounters_completed": self.state.encounters_completed,
            "bosses_defeated": self.state.bosses_defeated,
            "cards_collected": self.state.cards_collected,
            "gold_total": self.state.gold_total,
            "events_seen": list(self.state.events_seen),
            "remove_count": self.state.remove_count,
            "lang": self.state.lang,
        }

    def from_dict(self, data: dict) -> RunState:
        """Restore run state from a dictionary."""
        self.load_data()

        hero = deepcopy(self._all_heroes[data["hero_id"]])
        deck = []
        for card_data in data["deck"]:
            if card_data["id"] in self._all_cards:
                card = deepcopy(self._all_cards[card_data["id"]])
                card.upgraded = card_data.get("upgraded", False)
                deck.append(card)

        relics = []
        for rid in data["relics"]:
            if rid in self._all_relics:
                relics.append(deepcopy(self._all_relics[rid]))

        state = RunState(
            hero=hero,
            hp=data["hp"],
            max_hp=data["max_hp"],
            max_energy=data["max_energy"],
            deck=deck,
            relics=relics,
            gold=data["gold"],
            current_floor=data["current_floor"],
            phase=RunPhase(data["phase"]),
            story_flags=set(data.get("story_flags", [])),
            encounters_completed=data.get("encounters_completed", 0),
            bosses_defeated=data.get("bosses_defeated", 0),
            cards_collected=data.get("cards_collected", 0),
            gold_total=data.get("gold_total", 0),
            events_seen=set(data.get("events_seen", [])),
            remove_count=data.get("remove_count", 0),
            lang=data.get("lang", "zh"),
        )

        self.state = state
        self._generate_floor(state.current_floor)
        # Restore current node position
        state.floor_map.current_node = state.floor_map.start_node
        return state
