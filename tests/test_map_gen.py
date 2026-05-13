"""Tests for map generation and game engine."""

import pytest
from abyssal.engine.game import GameEngine, RunPhase, RoomType


class TestGameEngine:
    def test_start_run(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        assert state is not None
        assert state.hero.id == "knight"
        assert state.hp == 80
        assert state.max_hp == 80
        assert len(state.deck) == 10
        assert state.gold == 100
        assert state.current_floor == 1

    def test_map_generation(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        fm = state.floor_map
        assert fm is not None
        assert fm.floor_id == 1
        assert "start" in fm.nodes
        assert "boss" in fm.nodes
        assert fm.nodes["start"].visited

    def test_move_to_combat(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        available = engine.get_available_nodes()
        assert len(available) > 0

        # Move to first combat
        combat_nodes = [n for n in available if "_c" in n or "c1" in n or "c2" in n]
        if combat_nodes:
            result = engine.move_to_node(combat_nodes[0])
            assert result
            assert state.phase == RunPhase.COMBAT

    def test_encounter_generation(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        engine.move_to_node("c1")
        enemies = engine.get_encounter_enemies()
        assert len(enemies) > 0
        assert enemies[0].floor == 1

    def test_card_reward_generation(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        rewards = engine.generate_card_rewards(3)
        assert len(rewards) == 3
        for card in rewards:
            assert card.card_type.value != "curse"

    def test_game_serialization(self):
        engine = GameEngine()
        state = engine.start_run("knight")
        data = engine.to_dict()
        assert data["hero_id"] == "knight"
        assert data["hp"] == 80
        assert data["current_floor"] == 1

        # Restore
        engine2 = GameEngine()
        state2 = engine2.from_dict(data)
        assert state2.hero.id == "knight"
        assert state2.hp == 80

    def test_map_has_all_room_types(self):
        """Verify the map contains diverse room types."""
        engine = GameEngine()
        state = engine.start_run("knight")
        fm = state.floor_map

        types = {n.room_type for n in fm.nodes.values()}
        assert RoomType.START in types
        assert RoomType.COMBAT in types
        assert RoomType.BOSS in types
        # At least one of these should appear
        assert any(t in types for t in [RoomType.EVENT, RoomType.SHOP, RoomType.REST])
