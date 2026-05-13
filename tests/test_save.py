"""Tests for save/load system."""

import pytest
import json
from pathlib import Path
from abyssal.save.save_manager import SaveManager


class TestSaveManager:
    def test_save_and_load(self, tmp_path):
        sm = SaveManager()
        # Override save dir for testing
        import abyssal.save.save_manager as smod
        original_dir = smod.SAVE_DIR
        smod.SAVE_DIR = tmp_path

        try:
            data = {"hero_id": "knight", "hp": 50, "gold": 100, "_save_time": "test"}
            assert sm.save(1, data)
            loaded = sm.load(1)
            assert loaded is not None
            assert loaded["hero_id"] == "knight"
            assert loaded["hp"] == 50
        finally:
            smod.SAVE_DIR = original_dir

    def test_load_nonexistent(self):
        sm = SaveManager()
        result = sm.load(99)
        assert result is None

    def test_save_overwrite(self, tmp_path):
        sm = SaveManager()
        import abyssal.save.save_manager as smod
        original_dir = smod.SAVE_DIR
        smod.SAVE_DIR = tmp_path

        try:
            sm.save(1, {"hero_id": "knight"})
            sm.save(1, {"hero_id": "weaver"})
            loaded = sm.load(1)
            assert loaded["hero_id"] == "weaver"
        finally:
            smod.SAVE_DIR = original_dir

    def test_delete_save(self, tmp_path):
        sm = SaveManager()
        import abyssal.save.save_manager as smod
        original_dir = smod.SAVE_DIR
        smod.SAVE_DIR = tmp_path

        try:
            sm.save(1, {"hero_id": "knight"})
            assert sm.delete(1)
            assert sm.load(1) is None
        finally:
            smod.SAVE_DIR = original_dir

    def test_list_saves(self, tmp_path):
        sm = SaveManager()
        import abyssal.save.save_manager as smod
        original_dir = smod.SAVE_DIR
        smod.SAVE_DIR = tmp_path

        try:
            sm.save(1, {"hero_id": "knight", "current_floor": 1, "hp": 80, "max_hp": 80})
            sm.save(2, {"hero_id": "weaver", "current_floor": 2, "hp": 40, "max_hp": 65})
            saves = sm.list_saves()
            assert len(saves) == 2
        finally:
            smod.SAVE_DIR = original_dir

    def test_meta_progression(self, tmp_path):
        sm = SaveManager()
        import abyssal.save.save_manager as smod
        original_dir = smod.SAVE_DIR
        original_meta = smod.META_FILE
        smod.SAVE_DIR = tmp_path
        smod.META_FILE = tmp_path / "meta.json"

        try:
            meta = sm.load_meta()
            assert meta["abyssal_memory"] == 0
            assert "knight" in meta["unlocked_heroes"]

            new_total = sm.add_memory(100)
            assert new_total == 100

            meta = sm.load_meta()
            assert meta["abyssal_memory"] == 100
        finally:
            smod.SAVE_DIR = original_dir
            smod.META_FILE = original_meta
