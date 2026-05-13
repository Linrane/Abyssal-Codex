"""Status effect engine — keyword system, damage pipeline, effect resolution."""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class EffectType(Enum):
    DAMAGE = "damage"
    BLOCK = "block"
    APPLY_STATUS = "apply_status"
    DRAW = "draw"
    GAIN_ENERGY = "gain_energy"
    HEAL = "heal"
    DAMAGE_SELF = "damage_self"
    MULTI_HIT = "multi_hit"
    AOE = "aoe"
    CONDITIONAL_DAMAGE = "conditional_damage"
    SET_STANCE = "set_stance"
    REMOVE_STATUS = "remove_status"
    EXHAUST = "exhaust"


class StatusType:
    """All keyword/status types in the game."""
    VULNERABLE = "vulnerable"
    WEAK = "weak"
    POISON = "poison"
    CHARGE = "charge"
    DODGE = "dodge"
    REGEN = "regen"
    THORNS = "thorns"
    FREEZE = "freeze"
    RESONANCE = "resonance"
    BLOODRAGE = "bloodrage"
    STANCE_ATTACK = "attack"
    STANCE_DEFENSE = "defense"
    STANCE_GALE = "gale"

    # Keywords that are tracked as statuses on player/enemy
    STATUS_LIST = [
        VULNERABLE, WEAK, POISON, CHARGE, DODGE,
        REGEN, THORNS, FREEZE, RESONANCE, BLOODRAGE,
    ]


@dataclass
class Status:
    """A status effect on a combatant."""
    name: str
    stacks: int = 0
    duration: int = 0  # 0 = permanent until removed; >0 = ticks down each turn


class Combatant:
    """Base class for anything that fights (player or enemy)."""

    def __init__(self, name: str, max_hp: int, base_damage: int = 0):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.block = 0
        self.base_damage = base_damage
        self.statuses: dict[str, Status] = {}
        self.alive = True

    def apply_status(self, name: str, stacks: int = 1, duration: int = 0) -> None:
        if name in self.statuses:
            self.statuses[name].stacks += stacks
            if duration > 0:
                self.statuses[name].duration = max(self.statuses[name].duration, duration)
        else:
            self.statuses[name] = Status(name=name, stacks=stacks, duration=duration)

    def remove_status(self, name: str) -> None:
        self.statuses.pop(name, None)

    def has_status(self, name: str) -> bool:
        return name in self.statuses and self.statuses[name].stacks > 0

    def get_status_stacks(self, name: str) -> int:
        if name in self.statuses:
            return self.statuses[name].stacks
        return 0

    def add_block(self, amount: int) -> None:
        self.block += amount

    def take_damage(self, amount: int, attacker: Optional["Combatant"] = None) -> int:
        """Deal damage, reduced by block first. Returns actual HP lost."""
        if amount <= 0:
            return 0

        # Apply vulnerable multiplier
        if self.has_status(StatusType.VULNERABLE):
            amount = int(amount * 1.5)

        # Apply weak multiplier from attacker
        if attacker and attacker.has_status(StatusType.WEAK):
            amount = int(amount * 0.75)

        # Apply bloodrage bonus from attacker
        if attacker and attacker.has_status(StatusType.BLOODRAGE):
            hp_percent = attacker.hp / attacker.max_hp
            bloodrage_bonus = 1.0 + (1.0 - hp_percent) * 0.5 * attacker.get_status_stacks(StatusType.BLOODRAGE)
            amount = int(amount * bloodrage_bonus)

        # Apply stance attack bonus
        if attacker and attacker.has_status(StatusType.STANCE_ATTACK):
            amount = int(amount * 1.2)

        # Reduce block first
        if self.block > 0:
            if amount <= self.block:
                self.block -= amount
                # Thorns reflection
                if self.has_status(StatusType.THORNS):
                    if attacker:
                        thorn_dmg = self.get_status_stacks(StatusType.THORNS)
                        attacker.take_damage(thorn_dmg)
                return 0
            else:
                amount -= self.block
                self.block = 0

        # Apply freeze - skip action
        # Freeze is checked at intent execution time

        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

        # Thorns reflection
        if self.has_status(StatusType.THORNS) and attacker:
            thorn_dmg = self.get_status_stacks(StatusType.THORNS)
            attacker.take_damage(thorn_dmg)

        return amount

    def heal(self, amount: int) -> int:
        """Heal HP. Returns actual amount healed."""
        old_hp = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - old_hp

    def tick_statuses(self) -> list[str]:
        """Tick down status durations. Returns list of expired status names."""
        expired = []
        for name, status in list(self.statuses.items()):
            if name == StatusType.POISON and status.stacks > 0:
                self.take_damage(status.stacks)
                status.stacks = max(0, status.stacks - 1)
                if status.stacks <= 0:
                    expired.append(name)

            elif name == StatusType.REGEN and status.stacks > 0:
                self.heal(status.stacks)
                status.stacks = max(0, status.stacks - 1)
                if status.stacks <= 0:
                    expired.append(name)

            elif status.duration > 0:
                status.duration -= 1
                if status.duration <= 0:
                    expired.append(name)

        for name in expired:
            self.statuses.pop(name, None)

        return expired

    def reset_block(self) -> None:
        self.block = 0


class EffectResolver:
    """Handles applying card effects to targets."""

    def __init__(self, player: Combatant, enemies: list[Combatant]):
        self.player = player
        self.enemies = enemies

    def resolve(
        self,
        effect_type: str,
        value: int = 0,
        status: str = "",
        duration: int = 0,
        secondary_value: int = 0,
        condition: str = "",
        condition_value: int = 0,
        target_type: str = "single_enemy",
        target_index: int = 0,
    ) -> dict:
        """Resolve a single card effect. Returns a dict describing what happened."""
        result = {"type": effect_type, "message": "", "value": 0}

        if effect_type == "damage":
            target = self._get_target(target_type, target_index)
            if target and target.alive:
                dmg = target.take_damage(value, self.player)
                result["value"] = dmg
                result["message"] = f"Dealt {dmg} damage to {target.name}"

        elif effect_type == "block":
            # Apply stance defense bonus
            if self.player.has_status(StatusType.STANCE_DEFENSE):
                value = int(value * 1.3)
            self.player.add_block(value)
            result["value"] = value
            result["message"] = f"Gained {value} block"

        elif effect_type == "apply_status":
            target = self.player if target_type == "self" else self._get_target(target_type, target_index)
            if target and target.alive:
                target.apply_status(status, value, duration)
                result["value"] = value
                result["message"] = f"Applied {value} {status} to {target.name}"

        elif effect_type == "draw":
            result["value"] = value
            result["message"] = f"Draw {value} card(s)"

        elif effect_type == "gain_energy":
            result["value"] = value
            result["message"] = f"Gained {value} energy"

        elif effect_type == "heal":
            healed = self.player.heal(value)
            result["value"] = healed
            result["message"] = f"Healed {healed} HP"

        elif effect_type == "damage_self":
            dmg = self.player.take_damage(value)
            result["value"] = dmg
            result["message"] = f"Lost {dmg} HP"

        elif effect_type == "multi_hit":
            target = self._get_target(target_type, target_index)
            if target and target.alive:
                total_dmg = 0
                for _ in range(secondary_value):
                    dmg = target.take_damage(value, self.player)
                    total_dmg += dmg
                result["value"] = total_dmg
                result["message"] = f"Dealt {total_dmg} damage in {secondary_value} hits"

        elif effect_type == "conditional_damage":
            target = self._get_target(target_type, target_index)
            if target and target.alive:
                if condition == "charge" and self.player.get_status_stacks(StatusType.CHARGE) >= condition_value:
                    dmg = target.take_damage(value, self.player)
                    result["value"] = dmg
                    result["message"] = f"Bonus: dealt {dmg} damage"

        elif effect_type == "set_stance":
            # Clear all stance statuses first
            for s in [StatusType.STANCE_ATTACK, StatusType.STANCE_DEFENSE, StatusType.STANCE_GALE]:
                self.player.remove_status(s)
            stance_map = {
                "attack": StatusType.STANCE_ATTACK,
                "defense": StatusType.STANCE_DEFENSE,
                "gale": StatusType.STANCE_GALE,
            }
            stance_name = stance_map.get(status, status)
            self.player.apply_status(stance_name, value, duration)
            result["value"] = value
            result["message"] = f"Entered {status} stance"

        return result

    def _get_target(self, target_type: str, target_index: int = 0) -> Optional[Combatant]:
        """Get the target combatant based on type."""
        if target_type == "self" or target_type == "none":
            return self.player
        if target_type == "single_enemy" and 0 <= target_index < len(self.enemies):
            for i, e in enumerate(self.enemies):
                if e.alive:
                    if target_index == 0:
                        return e
                    target_index -= 1
        if target_type == "all_enemies":
            return next((e for e in self.enemies if e.alive), None)
        return next((e for e in self.enemies if e.alive), None)

    def get_alive_enemies(self) -> list[Combatant]:
        return [e for e in self.enemies if e.alive]

    def all_enemies_dead(self) -> bool:
        return not any(e.alive for e in self.enemies)
