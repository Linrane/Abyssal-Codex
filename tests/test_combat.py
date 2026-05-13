"""Tests for the combat engine."""

import pytest
from abyssal.data.cards import Card, CardEffect, CardType, Rarity
from abyssal.data.enemies import Enemy, AIBehavior, Intent, IntentType
from abyssal.engine.combat import CombatEngine, CombatState, CombatPhase


def make_card(cid, card_type="attack", cost=1, effects=None, exhaust=False):
    """Helper to create test cards."""
    return Card(
        id=cid,
        name_key=f"card.{cid}",
        desc_key=f"card.{cid}.desc",
        card_type=CardType(card_type),
        rarity=Rarity.COMMON,
        cost=cost,
        effects=effects or [CardEffect(type="damage", value=6)],
        exhaust=exhaust,
    )


def make_enemy(eid="test_goblin", max_hp=30, base_damage=5):
    """Helper to create test enemies."""
    return Enemy(
        id=eid,
        name_key=eid,
        desc_key=f"{eid}.desc",
        max_hp=max_hp,
        base_damage=base_damage,
        floor=1,
        behaviors=[AIBehavior(pattern=[Intent(type=IntentType.ATTACK, value=base_damage)])],
    )


class TestCombatCreation:
    def test_create_combat(self):
        deck = [make_card("strike", cost=1) for _ in range(10)]
        enemies = [make_enemy("goblin", 30, 5)]

        combat = CombatEngine.create(
            player_hp=80,
            player_max_hp=80,
            max_energy=3,
            deck=deck,
            enemy_defs=enemies,
        )

        assert combat.state.player.hp == 80
        assert combat.state.player.max_hp == 80
        assert combat.state.max_energy == 3
        assert combat.state.energy == 3
        assert len(combat.state.draw_pile) == 5  # 10 - 5 drawn
        assert len(combat.state.hand) == 5
        assert combat.state.phase == CombatPhase.PLAYER_TURN
        assert combat.state.turn == 1

    def test_floor_effect_combat_start(self):
        deck = [make_card("strike") for _ in range(10)]
        enemies = [make_enemy("goblin", 30)]
        floor_effect = {"type": "combat_start", "status": "vulnerable", "value": 1}

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies, floor_effect=floor_effect,
        )

        assert combat.state.player.has_status("vulnerable")
        assert combat.state.enemies[0].has_status("vulnerable")


class TestCombatFlow:
    def test_play_card_reduces_energy(self):
        deck = [make_card("strike", cost=1) for _ in range(10)]
        enemies = [make_enemy("goblin", 30)]

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        initial_energy = combat.state.energy
        combat.play_card(0, 0)
        assert combat.state.energy == initial_energy - 1

    def test_play_card_deals_damage(self):
        deck = [make_card("strike", cost=1) for _ in range(10)]
        enemies = [make_enemy("goblin", 30)]

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        enemy_hp_before = combat.state.enemies[0].hp
        combat.play_card(0, 0)
        assert combat.state.enemies[0].hp < enemy_hp_before

    def test_cant_play_unaffordable_card(self):
        deck = [make_card("strike", cost=1) for _ in range(5)]
        deck.append(make_card("heavy", cost=5))
        enemies = [make_enemy("goblin", 30)]

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        # Find the expensive card
        for i, card in enumerate(combat.state.hand):
            if card.cost == 5:
                result = combat.play_card(i, 0)
                assert result == False

    def test_end_turn_executes_enemy(self):
        deck = [make_card("strike") for _ in range(10)]
        enemies = [make_enemy("goblin", 30, 5)]

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        player_hp_before = combat.state.player.hp
        combat.end_player_turn()

        # Enemy should have attacked
        assert combat.state.player.hp < player_hp_before
        # Should be player's turn again
        assert combat.state.phase == CombatPhase.PLAYER_TURN

    def test_victory_when_enemies_dead(self):
        deck = [make_card("strike", cost=1, effects=[CardEffect(type="damage", value=50)]) for _ in range(10)]
        enemies = [make_enemy("goblin", 10)]

        combat = CombatEngine.create(
            player_hp=80, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        combat.play_card(0, 0)
        assert combat.state.won
        assert combat.state.phase == CombatPhase.COMBAT_END

    def test_defeat_when_player_dies(self):
        deck = [make_card("strike") for _ in range(10)]
        enemies = [make_enemy("boss", 999, 100)]

        combat = CombatEngine.create(
            player_hp=5, player_max_hp=80, max_energy=3,
            deck=deck, enemy_defs=enemies,
        )

        combat.end_player_turn()
        assert combat.state.lost
