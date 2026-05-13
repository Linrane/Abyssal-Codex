"""Tests for the effects engine."""

import pytest
from abyssal.engine.effects import Combatant, EffectResolver, StatusType


class TestCombatant:
    def test_take_damage(self):
        c = Combatant("test", max_hp=50)
        c.take_damage(10)
        assert c.hp == 40

    def test_take_damage_with_block(self):
        c = Combatant("test", max_hp=50)
        c.add_block(8)
        c.take_damage(5)
        assert c.hp == 50
        assert c.block == 3

    def test_take_damage_block_partial(self):
        c = Combatant("test", max_hp=50)
        c.add_block(5)
        c.take_damage(10)
        assert c.hp == 45
        assert c.block == 0

    def test_vulnerable_multiplier(self):
        c = Combatant("test", max_hp=60)
        c.apply_status(StatusType.VULNERABLE, 1)
        c.take_damage(10)
        assert c.hp == 45  # 60 - 15

    def test_weak_multiplier(self):
        attacker = Combatant("attacker", max_hp=30)
        defender = Combatant("defender", max_hp=60)
        attacker.apply_status(StatusType.WEAK, 1)
        defender.take_damage(10, attacker)
        assert defender.hp == 53  # 60 - 7 (10 * 0.75)

    def test_thorns_reflect(self):
        attacker = Combatant("attacker", max_hp=50)
        defender = Combatant("defender", max_hp=60)
        defender.apply_status(StatusType.THORNS, 3)
        # Attacker attacks defender; defender takes 10 damage, reflects 3 thorns
        defender.take_damage(10, attacker)
        assert defender.hp == 50  # 60 - 10
        assert attacker.hp == 47  # 50 - 3 (thorns reflect)

    def test_poison_tick(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.POISON, 3)
        expired = c.tick_statuses()
        assert c.hp == 47  # 50 - 3
        assert c.get_status_stacks(StatusType.POISON) == 2

    def test_regen_tick(self):
        c = Combatant("test", max_hp=50)
        c.hp = 30
        c.apply_status(StatusType.REGEN, 5)
        c.tick_statuses()
        assert c.hp == 35  # 30 + 5

    def test_duration_decay(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.VULNERABLE, 1, duration=2)
        c.tick_statuses()
        assert c.has_status(StatusType.VULNERABLE)
        c.tick_statuses()
        assert not c.has_status(StatusType.VULNERABLE)

    def test_death(self):
        c = Combatant("test", max_hp=20)
        c.take_damage(25)
        assert not c.alive
        assert c.hp == 0

    def test_heal(self):
        c = Combatant("test", max_hp=50)
        c.hp = 20
        healed = c.heal(15)
        assert healed == 15
        assert c.hp == 35

    def test_heal_no_overflow(self):
        c = Combatant("test", max_hp=50)
        c.hp = 45
        healed = c.heal(20)
        assert healed == 5
        assert c.hp == 50


class TestBloodrage:
    def test_bloodrage_scaling(self):
        attacker = Combatant("attacker", max_hp=100)
        defender = Combatant("defender", max_hp=200)
        attacker.apply_status(StatusType.BLOODRAGE, 3)
        attacker.hp = 20  # 20% HP -> 80% missing
        # bloodrage bonus: 1.0 + 0.8 * 0.5 * 3 = 1.0 + 1.2 = 2.2
        defender.take_damage(10, attacker)
        assert defender.hp == 200 - 22  # 10 * 2.2

    def test_no_bloodrage_at_full_hp(self):
        attacker = Combatant("attacker", max_hp=100)
        defender = Combatant("defender", max_hp=100)
        attacker.apply_status(StatusType.BLOODRAGE, 3)
        # Full HP, no bonus
        defender.take_damage(10, attacker)
        assert defender.hp == 90  # 10 * 1.0


class TestStance:
    def test_attack_stance(self):
        attacker = Combatant("attacker", max_hp=50)
        defender = Combatant("defender", max_hp=80)
        attacker.apply_status(StatusType.STANCE_ATTACK, 1)
        defender.take_damage(10, attacker)
        assert defender.hp == 68  # 80 - 12 (10 * 1.2)

    def test_defense_stance_block(self):
        # Defense stance handled by combat engine when playing block cards
        pass


class TestEffectResolver:
    def test_resolve_damage(self):
        player = Combatant("hero", max_hp=80)
        enemy = Combatant("goblin", max_hp=30)
        resolver = EffectResolver(player, [enemy])
        result = resolver.resolve("damage", value=6, target_type="single_enemy", target_index=0)
        assert result["value"] == 6
        assert enemy.hp == 24

    def test_resolve_block(self):
        player = Combatant("hero", max_hp=80)
        enemy = Combatant("goblin", max_hp=30)
        resolver = EffectResolver(player, [enemy])
        result = resolver.resolve("block", value=5, target_type="self")
        assert result["value"] == 5
        assert player.block == 5

    def test_apply_status(self):
        player = Combatant("hero", max_hp=80)
        enemy = Combatant("goblin", max_hp=30)
        resolver = EffectResolver(player, [enemy])
        result = resolver.resolve("apply_status", status="vulnerable", value=2, duration=2, target_type="single_enemy", target_index=0)
        assert enemy.has_status("vulnerable")
        assert enemy.get_status_stacks("vulnerable") == 2


class TestStrength:
    def test_strength_adds_flat_damage(self):
        attacker = Combatant("attacker", max_hp=50)
        defender = Combatant("defender", max_hp=80)
        attacker.apply_status(StatusType.STRENGTH, 3)
        defender.take_damage(10, attacker)
        assert defender.hp == 67  # 80 - (10 + 3) = 67

    def test_strength_stacks(self):
        attacker = Combatant("attacker", max_hp=50)
        defender = Combatant("defender", max_hp=80)
        attacker.apply_status(StatusType.STRENGTH, 5)
        defender.take_damage(10, attacker)
        assert defender.hp == 65  # 80 - 15


class TestMetallic:
    def test_metallic_gives_block_per_turn(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.METALLIC, 4)
        c.tick_statuses()
        assert c.block == 4

    def test_metallic_stacks_accumulate_block(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.METALLIC, 3)
        c.tick_statuses()
        assert c.block == 3
        c.tick_statuses()
        assert c.block == 6  # accumulates


class TestIntangible:
    def test_intangible_reduces_damage_to_one(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.INTANGIBLE, 1)
        c.take_damage(30)
        assert c.hp == 49  # damage reduced to 1

    def test_intangible_does_not_reduce_one_damage(self):
        c = Combatant("test", max_hp=50)
        c.apply_status(StatusType.INTANGIBLE, 1)
        c.take_damage(1)
        assert c.hp == 49  # still takes 1
