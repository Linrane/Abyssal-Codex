"""Turn-based combat state machine."""

import random
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from abyssal.data.cards import Card, CardEffect, CardType, TargetType
from abyssal.data.enemies import Enemy, Intent
from abyssal.data.relics import Relic
from abyssal.engine.effects import Combatant, EffectResolver, StatusType


class CombatPhase(Enum):
    PLAYER_TURN = "player_turn"
    ENEMY_TURN = "enemy_turn"
    ROUND_END = "round_end"
    COMBAT_END = "combat_end"


@dataclass
class CombatState:
    """Full state of a combat encounter."""
    player: Combatant
    enemies: list[Combatant]
    deck: list[Card]
    hand: list[Card] = field(default_factory=list)
    draw_pile: list[Card] = field(default_factory=list)
    discard_pile: list[Card] = field(default_factory=list)
    exhaust_pile: list[Card] = field(default_factory=list)
    energy: int = 3
    max_energy: int = 3
    turn: int = 0
    phase: CombatPhase = CombatPhase.PLAYER_TURN
    draw_per_turn: int = 5
    relics: list[Relic] = field(default_factory=list)
    floor_effect: dict = field(default_factory=dict)
    combat_log: list[str] = field(default_factory=list)
    gold_earned: int = 0
    cards_rewarded: list[Card] = field(default_factory=list)
    relic_rewarded: Optional[Relic] = None
    won: bool = False
    lost: bool = False
    used_snake_skin: bool = False

    def __post_init__(self):
        if not self.draw_pile and self.deck:
            self.draw_pile = list(self.deck)
            random.shuffle(self.draw_pile)

    def log(self, msg: str) -> None:
        self.combat_log.append(msg)


class CombatEngine:
    """Manages a single combat encounter."""

    def __init__(self, state: CombatState):
        self.state = state
        self.resolver = EffectResolver(state.player, state.enemies)
        self._selected_enemy_index = 0
        self._enemy_intents: list[Optional[Intent]] = [None] * len(state.enemies)
        self._applied_floor_effect = False

    @classmethod
    def create(
        cls,
        player_hp: int,
        player_max_hp: int,
        max_energy: int,
        deck: list[Card],
        enemy_defs: list[Enemy],
        relics: Optional[list[Relic]] = None,
        floor_effect: Optional[dict] = None,
    ) -> "CombatEngine":
        """Factory method to create a combat from game state."""
        player = Combatant(name="Hero", max_hp=player_max_hp)
        player.hp = player_hp

        # Apply relic passive modifiers
        if relics:
            for relic in relics:
                passive = relic.passive
                if "max_hp" in passive:
                    player.max_hp += passive["max_hp"]
                    player.hp = min(player.hp, player.max_hp)
                    player.hp = max(player.hp, 1)  # HP can't go below 1 from passive
                if "max_energy" in passive:
                    max_energy += passive["max_energy"]
                if "draw_bonus" in passive:
                    pass  # Handled in draw phase

        enemies = []
        for ed in enemy_defs:
            enemy = Combatant(name=ed.name_key, max_hp=ed.max_hp, base_damage=ed.base_damage)
            enemies.append(enemy)

        # Deep copy deck to avoid mutating originals
        deck_copy = [deepcopy(c) for c in deck]
        random.shuffle(deck_copy)

        draw_bonus = 0
        if relics:
            for relic in relics:
                if "draw_bonus" in relic.passive:
                    draw_bonus += relic.passive["draw_bonus"]

        state = CombatState(
            player=player,
            enemies=enemies,
            deck=deck_copy,
            draw_pile=list(deck_copy),
            max_energy=max_energy,
            energy=max_energy,
            draw_per_turn=5 + draw_bonus,
            relics=relics or [],
            floor_effect=floor_effect or {},
        )

        engine = cls(state)
        engine._setup_combat_start()
        return engine

    def _setup_combat_start(self) -> None:
        """Apply combat start effects from relics and floor."""
        for relic in self.state.relics:
            if relic.on_combat_start:
                self._apply_relic_trigger(relic.on_combat_start)
            if relic.max_charges > 0:
                relic.charges = relic.max_charges

        # Floor effect: combat start
        fe = self.state.floor_effect
        if fe.get("type") == "combat_start":
            status = fe.get("status", "")
            value = fe.get("value", 1)
            self.state.player.apply_status(status, value)
            for e in self.state.enemies:
                e.apply_status(status, value)
            self.state.log(f"Floor effect: Everyone gains {value} {status}")

        # Start player turn
        self._start_player_turn()

    def _start_player_turn(self) -> None:
        """Begin the player's turn."""
        self.state.turn += 1
        self.state.phase = CombatPhase.PLAYER_TURN
        self.state.player.reset_block()

        # Handle freeze on player
        if self.state.player.has_status(StatusType.FREEZE):
            self.state.log("You are frozen and skip your turn!")
            self.state.player.remove_status(StatusType.FREEZE)
            self._start_enemy_turn()
            return

        # Energy reset
        bonus_energy = 0
        if self.state.floor_effect.get("type") == "energy_bonus":
            bonus_energy = self.state.floor_effect.get("value", 0)

        self.state.energy = self.state.max_energy + bonus_energy

        # Floor 3: cost fluctuation
        if self.state.floor_effect.get("cost_fluctuation"):
            pass  # Handled when playing cards

        # Apply turn start relic effects
        for relic in self.state.relics:
            if relic.on_turn_start:
                self._apply_relic_trigger(relic.on_turn_start)

        # Floor effect: turn-based
        fe = self.state.floor_effect
        if fe.get("type") == "turn_start" and self.state.turn >= fe.get("turn", 0):
            status = fe.get("status", "")
            value = fe.get("value", 1)
            self.state.player.apply_status(status, value)
            for e in self.state.enemies:
                e.apply_status(status, value)
            self.state.log(f"Floor effect: Everyone gains {value} {status}")

        # Determine enemy intents for this round
        self._determine_enemy_intents()

        # Handle stance: gale bonus draw
        if self.state.player.has_status(StatusType.STANCE_GALE):
            self._draw_cards(1)

        # Draw hand
        self._draw_cards(self.state.draw_per_turn)

        # Innate cards go to hand immediately at combat start
        if self.state.turn == 1:
            for card in self.state.draw_pile[:]:
                if card.innate:
                    if len(self.state.hand) < 10:  # Max hand size
                        self.state.hand.append(card)
                        self.state.draw_pile.remove(card)

    def _draw_cards(self, count: int) -> None:
        """Draw cards from draw pile, reshuffling discard if needed."""
        for _ in range(count):
            if not self.state.draw_pile:
                if not self.state.discard_pile:
                    break
                self.state.draw_pile = list(self.state.discard_pile)
                self.state.discard_pile = []
                random.shuffle(self.state.draw_pile)
                self.state.log("Reshuffled discard pile into draw pile.")

            if self.state.draw_pile:
                card = self.state.draw_pile.pop()
                if len(self.state.hand) < 10:
                    self.state.hand.append(card)

    def play_card(self, hand_index: int, target_index: int = 0) -> bool:
        """Play a card from hand. Returns True if successful."""
        if self.state.phase != CombatPhase.PLAYER_TURN:
            return False

        if hand_index < 0 or hand_index >= len(self.state.hand):
            return False

        card = self.state.hand[hand_index]

        # Calculate cost with floor fluctuation
        cost = card.get_cost()
        if self.state.floor_effect.get("cost_fluctuation"):
            fluctuation = random.choice([-1, 0, 0, 0, 1])
            cost = max(1, cost + fluctuation)

        if cost > self.state.energy:
            return False

        # Pay energy
        self.state.energy -= cost

        # Remove from hand
        self.state.hand.pop(hand_index)

        # Apply card effects
        effects = card.get_effects()
        for effect in effects:
            e_type = effect.type if isinstance(effect, CardEffect) else effect.get("type", "")
            e_value = effect.value if isinstance(effect, CardEffect) else effect.get("value", 0)
            e_status = effect.status if isinstance(effect, CardEffect) else effect.get("status", "")
            e_duration = effect.duration if isinstance(effect, CardEffect) else effect.get("duration", 0)
            e_secondary = effect.secondary_value if isinstance(effect, CardEffect) else effect.get("secondary_value", 0)
            e_condition = effect.condition if isinstance(effect, CardEffect) else effect.get("condition", "")
            e_cond_value = effect.condition_value if isinstance(effect, CardEffect) else effect.get("condition_value", 0)

            result = self.resolver.resolve(
                effect_type=e_type,
                value=e_value,
                status=e_status,
                duration=e_duration,
                secondary_value=e_secondary,
                condition=e_condition,
                condition_value=e_cond_value,
                target_type=card.target.value,
                target_index=target_index,
            )
            if result["message"]:
                self.state.log(result["message"])

            # Handle draw effects
            if e_type == "draw":
                self._draw_cards(result["value"])
            if e_type == "gain_energy":
                self.state.energy += result["value"]

        # Determine destination
        if card.exhaust or card.card_type == CardType.POWER:
            self.state.exhaust_pile.append(card)
        else:
            self.state.discard_pile.append(card)

        # Check for relic triggers on card played
        for relic in self.state.relics:
            if relic.on_card_played:
                self._apply_relic_trigger(relic.on_card_played)

        # Check win condition
        if self.resolver.all_enemies_dead():
            self.state.phase = CombatPhase.COMBAT_END
            self.state.won = True

        return True

    def end_player_turn(self) -> None:
        """End the player's turn and begin enemy turn."""
        if self.state.phase != CombatPhase.PLAYER_TURN:
            return

        # Discard remaining hand
        for card in self.state.hand:
            self.state.discard_pile.append(card)
        self.state.hand = []

        self.state.player.reset_block()
        self._start_enemy_turn()

    def _start_enemy_turn(self) -> None:
        """Execute enemy turns."""
        self.state.phase = CombatPhase.ENEMY_TURN

        for i, enemy in enumerate(self.state.enemies):
            if not enemy.alive:
                continue
            if enemy.has_status(StatusType.FREEZE):
                enemy.remove_status(StatusType.FREEZE)
                self.state.log(f"{enemy.name} is frozen and skips its turn!")
                continue

            intent = self._enemy_intents[i]
            if intent:
                self._execute_enemy_intent(enemy, intent)

            # Check player death
            if not self.state.player.alive:
                self.state.phase = CombatPhase.COMBAT_END
                self.state.lost = True
                return

        if self.state.phase != CombatPhase.COMBAT_END:
            self._end_round()

    def _execute_enemy_intent(self, enemy: Combatant, intent: Intent) -> None:
        """Execute a single enemy's intent."""
        if intent.type.value == "attack":
            dmg = intent.value
            self.state.player.take_damage(dmg, enemy)
            self.state.log(f"{enemy.name} attacks for {dmg} damage!")

        elif intent.type.value == "defend":
            enemy.add_block(intent.value)
            self.state.log(f"{enemy.name} defends for {intent.value} block.")

        elif intent.type.value == "skill":
            if intent.status:
                if intent.status in ("vulnerable", "weak", "poison", "freeze"):
                    self.state.player.apply_status(intent.status, intent.status_value, 2)
                    self.state.log(f"{enemy.name} applies {intent.status_value} {intent.status} to you!")
                elif intent.status == "dodge":
                    enemy.apply_status(intent.status, intent.status_value, 2)
                    self.state.log(f"{enemy.name} gains {intent.status_value} {intent.status}!")

        elif intent.type.value == "special":
            if intent.status:
                self.state.player.apply_status(intent.status, intent.status_value, 3)
                self.state.log(f"{enemy.name} uses a special: {intent.status} {intent.status_value}!")

    def _end_round(self) -> None:
        """End of round processing."""
        self.state.phase = CombatPhase.ROUND_END

        # Tick statuses
        self.state.player.tick_statuses()
        for enemy in self.state.enemies:
            if enemy.alive:
                enemy.tick_statuses()

        # Apply turn end relic effects
        for relic in self.state.relics:
            if relic.on_turn_end:
                self._apply_relic_trigger(relic.on_turn_end)

        # Check player death from status ticks
        if not self.state.player.alive:
            self.state.phase = CombatPhase.COMBAT_END
            self.state.lost = True
            return

        # Check enemy death from status ticks
        if self.resolver.all_enemies_dead():
            self.state.phase = CombatPhase.COMBAT_END
            self.state.won = True
            return

        # Remove dead enemies
        self.state.enemies = [e for e in self.state.enemies if e.alive]

        self._start_player_turn()

    def _determine_enemy_intents(self) -> None:
        """Determine what each enemy will do this round."""
        for i, enemy_def in enumerate(self.state.enemies):
            # Simple intent generation based on pattern
            # In full implementation, this uses the enemy's AI behavior
            intent = Intent(
                type=type("IntentType", (), {"value": "attack"})(),
                value=max(1, int(enemy_def.base_damage * (0.8 + random.random() * 0.4))),
            )
            self._enemy_intents[i] = intent

    def _apply_relic_trigger(self, trigger: dict) -> None:
        """Apply a relic's trigger effect."""
        effect = trigger.get("effect", trigger.get("type", ""))
        value = trigger.get("value", 0)

        if effect == "heal":
            self.state.player.heal(value)
        elif effect == "block":
            self.state.player.add_block(value)
        elif effect == "gain_energy":
            self.state.energy += value
        elif effect == "apply_random_enemy":
            alive = [e for e in self.state.enemies if e.alive]
            if alive:
                target = random.choice(alive)
                status = trigger.get("status", "poison")
                target.apply_status(status, value)
        elif effect == "refresh_charges":
            pass  # Handle at relic level

    def use_snake_skin(self) -> bool:
        """Redraw hand using Snake Skin relic. Returns True if used."""
        if self.state.used_snake_skin:
            return False

        has_relic = any(r.id == "snake_skin" and r.charges > 0 for r in self.state.relics)
        if not has_relic:
            return False

        # Discard hand and redraw
        for card in self.state.hand:
            self.state.discard_pile.append(card)
        self.state.hand = []
        self._draw_cards(self.state.draw_per_turn)
        self.state.used_snake_skin = True

        for r in self.state.relics:
            if r.id == "snake_skin":
                r.charges -= 1

        return True

    def try_phoenix_revive(self) -> bool:
        """Check if phoenix feather should revive the player. Returns True if revived."""
        for r in self.state.relics:
            if r.id == "phoenix_feather" and r.charges > 0:
                r.charges -= 1
                revive_hp = int(self.state.player.max_hp * r.on_death.get("value", 0.5))
                self.state.player.hp = max(1, revive_hp)
                self.state.player.alive = True
                self.state.lost = False
                self.state.phase = CombatPhase.PLAYER_TURN
                self.state.log("Phoenix Feather revives you!")
                return True
        return False

    def get_available_targets(self) -> list[int]:
        """Return indices of alive enemies."""
        return [i for i, e in enumerate(self.state.enemies) if e.alive]

    def get_enemy_intent_display(self, index: int) -> str:
        """Get a display string for an enemy's intent."""
        if index >= len(self._enemy_intents) or self._enemy_intents[index] is None:
            return "?"
        intent = self._enemy_intents[index]
        icons = {"attack": "⚔", "defend": "🛡", "skill": "💀", "special": "❓"}
        return icons.get(intent.type.value, "?")
