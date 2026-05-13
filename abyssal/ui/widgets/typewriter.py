"""Typewriter text effect for narrative display."""

import time


def typewriter_print(
    text: str,
    delay: float = 0.03,
    speed: str = "normal",
    callback=None,
) -> None:
    """Print text character by character with typewriter effect.

    This is designed to work with Rich Live display.
    For Rich integration, yields chunks of text over time.

    Args:
        text: The text to display
        delay: Base delay per character
        speed: 'fast', 'normal', or 'slow'
        callback: Called with partial text as it's revealed
    """
    delays = {"fast": 0.01, "normal": 0.03, "slow": 0.06}
    char_delay = delays.get(speed, delay)

    if callback:
        displayed = ""
        for char in text:
            displayed += char
            time.sleep(char_delay)
            callback(displayed)
    else:
        for char in text:
            print(char, end="", flush=True)
            time.sleep(char_delay)


def typewriter_generator(text: str, speed: str = "normal"):
    """Generator that yields progressively longer text chunks."""
    delays = {"fast": 0.008, "normal": 0.02, "slow": 0.05}
    char_delay = delays.get(speed, 0.02)

    displayed = ""
    for char in text:
        displayed += char
        yield displayed
        # In a real Rich Live context, we'd sleep between yields
        # time.sleep(char_delay)
