"""Enemy AI behavior system.

Uses behavior patterns from enemy definitions to determine intent each round.
Supports: cycle, random, conditional patterns, and phase transitions.
"""

import random
from typing import Optional

from abyssal.data.enemies import AIBehavior, Enemy, Intent, IntentType
from abyssal.engine.effects import Combatant


class EnemyAI:
    """Manages enemy behavior during combat."""

    def __init__(self, enemy: Combatant, enemy_def: Enemy):
        self.enemy = enemy
        self.enemy_def = enemy_def
        self._pattern_index = 0
        self._current_phase = 1
        self._phase_locked = False

    @property
    def current_phase(self) -> int:
        return self._current_phase

    def determine_intent(self) -> Intent:
        """Determine what the enemy will do this turn."""
        # Check phase transition
        self._check_phase_transition()

        behavior = self._get_behavior()
        if not behavior or not behavior.pattern:
            # Default: simple attack
            dmg = max(1, self.enemy.base_damage)
            return Intent(type=IntentType.ATTACK, value=dmg)

        return self._next_intent(behavior)

    def _check_phase_transition(self) -> None:
        """Check if enemy should enter phase 2."""
        if self._phase_locked:
            return

        for b in self.enemy_def.behaviors:
            if isinstance(b, dict):
                b = AIBehavior.from_dict(b)
            if b.phase != self._current_phase + 1:
                continue

            if b.condition == "hp_below_50":
                hp_percent = self.enemy.hp / self.enemy.max_hp
                if hp_percent <= 0.5:
                    self._current_phase = b.phase
                    self._pattern_index = 0
                    self._phase_locked = True

    def _get_behavior(self) -> Optional[AIBehavior]:
        """Get the behavior for the current phase."""
        for b in self.enemy_def.behaviors:
            if isinstance(b, dict):
                b = AIBehavior.from_dict(b)
            if b.phase == self._current_phase:
                return b
        return None

    def _next_intent(self, behavior: AIBehavior) -> Intent:
        """Get the next intent from a behavior pattern."""
        if behavior.pattern_type == "cycle":
            idx = self._pattern_index % len(behavior.pattern)
            self._pattern_index += 1
            intent_data = behavior.pattern[idx]
            if isinstance(intent_data, dict):
                return Intent.from_dict(intent_data)
            return intent_data

        elif behavior.pattern_type == "random":
            intent_data = random.choice(behavior.pattern)
            if isinstance(intent_data, dict):
                return Intent.from_dict(intent_data)
            return intent_data

        elif behavior.pattern_type == "conditional":
            # Simple conditional: if player has status X, use pattern Y
            # For MVP, just cycle
            idx = self._pattern_index % len(behavior.pattern)
            self._pattern_index += 1
            intent_data = behavior.pattern[idx]
            if isinstance(intent_data, dict):
                return Intent.from_dict(intent_data)
            return intent_data

        # Fallback
        if behavior.pattern:
            intent_data = behavior.pattern[0]
            if isinstance(intent_data, dict):
                return Intent.from_dict(intent_data)
            return intent_data

        return Intent(type=IntentType.ATTACK, value=self.enemy.base_damage)


class AIController:
    """Manages AI for all enemies in combat."""

    def __init__(self, enemies: list[Combatant], enemy_defs: list[Enemy]):
        self._ais: list[EnemyAI] = []
        for enemy, defn in zip(enemies, enemy_defs):
            self._ais.append(EnemyAI(enemy, defn))

    def determine_all_intents(self) -> list[Intent]:
        """Get intents for all alive enemies."""
        intents = []
        for ai in self._ais:
            if ai.enemy.alive:
                intents.append(ai.determine_intent())
            else:
                intents.append(Intent(type=IntentType.ATTACK, value=0))
        return intents

    def get_intent_display(self, intent: Intent, lang: str = "en") -> str:
        """Get a display string for an intent."""
        icons = {
            "attack": "⚔️",
            "defend": "🛡️",
            "skill": "💀",
            "special": "❓",
        }
        icon = icons.get(intent.type.value, "?")

        if intent.type == IntentType.ATTACK:
            return f"{icon} {intent.value}"
        elif intent.type == IntentType.DEFEND:
            return f"{icon} {intent.value}"
        elif intent.type == IntentType.SKILL:
            return f"{icon} {intent.status}"
        elif intent.type == IntentType.SPECIAL:
            return f"{icon} {intent.status}"
        return f"{icon}"
