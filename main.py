#!/usr/bin/env python3
"""Abyssal Codex - Terminal Roguelike Card Game.

Entry point for the game. Handles command-line arguments and launches the game.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from abyssal.ui.app import GameApp


def main():
    """Main entry point."""
    try:
        app = GameApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\n  Game interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Fatal error: {e}")
        print("  Please report this issue on GitHub.")
        sys.exit(1)


if __name__ == "__main__":
    main()
