"""Event script interpreter for event encounters."""

import random
from copy import deepcopy
from typing import Optional

from abyssal.data.events import Event, EventChoice
from abyssal.engine.game import GameEngine


class EventRunner:
    """Runs event encounters and applies their effects."""

    def __init__(self, engine: GameEngine):
        self.engine = engine

    def run_event(self, event: Event) -> dict:
        """Prepare an event for display. Returns event data for UI."""
        state = self.engine.state

        # Check story flag prerequisites
        if event.story_flag_required and event.story_flag_required not in state.story_flags:
            return {"event": None, "choices": [], "blocked": True}

        # Check class-specific events
        if event.character_class and event.character_class != state.hero.id:
            return {"event": None, "choices": [], "blocked": True}

        # Filter available choices
        available_choices = []
        for choice in event.choices:
            if not self._check_requirements(choice):
                continue
            available_choices.append(choice)

        return {
            "event": event,
            "choices": available_choices,
        }

    def execute_choice(self, event: Event, choice: EventChoice) -> dict:
        """Execute a player's choice. Returns result dictionary."""
        result = {"success": True, "message": "", "effects": []}
        state = self.engine.state

        # Check chance
        if choice.chance < 1.0:
            roll = random.random()
            if roll > choice.chance:
                result["success"] = False
                result["message"] = choice.fail_text_key
                return result

        # Apply effects
        for effect in choice.effects:
            effect_type = effect.get("type", "")
            value = effect.get("value", 0)

            if effect_type == "heal_percent":
                heal_amt = int(state.max_hp * value)
                state.hp = min(state.max_hp, state.hp + heal_amt)
                result["effects"].append(f"Healed {heal_amt} HP")

            elif effect_type == "remove_gold":
                self.engine.spend_gold(value)
                result["effects"].append(f"Lost {value} gold")

            elif effect_type == "add_random_relic":
                relic = self.engine.generate_relic_reward()
                if relic:
                    state.relics.append(relic)
                    result["effects"].append(f"Got relic: {relic.name_key}")

            elif effect_type == "add_random_rare_card":
                pool = [c for c in self.engine.get_card_pool() if c.rarity.value == "rare"]
                if pool:
                    card = random.choice(pool)
                    self.engine.add_card_to_deck(card)
                    result["effects"].append(f"Got card: {card.name_key}")

            elif effect_type == "add_random_legendary_card":
                pool = [c for c in self.engine._all_cards.values()
                        if c.rarity.value == "legendary" and c.card_type.value != "curse"]
                if pool:
                    card = deepcopy(random.choice(pool))
                    self.engine.add_card_to_deck(card)
                    result["effects"].append(f"Got legendary: {card.name_key}")

            elif effect_type == "add_random_card":
                pool = self.engine.get_card_pool()
                if pool:
                    card = random.choice(pool)
                    self.engine.add_card_to_deck(card)
                    result["effects"].append(f"Got card: {card.name_key}")

            elif effect_type == "add_specific_card":
                card_id = effect.get("card_id", "")
                if card_id in self.engine._all_cards:
                    card = deepcopy(self.engine._all_cards[card_id])
                    self.engine.add_card_to_deck(card)
                    result["effects"].append(f"Got card: {card.name_key}")

            elif effect_type == "add_curse_card":
                card_id = effect.get("card_id", "doubt")
                cards = self.engine._all_cards
                if card_id in cards:
                    from copy import deepcopy
                    self.engine.add_card_to_deck(deepcopy(cards[card_id]))
                    result["effects"].append(f"Added curse: {card_id}")

            elif effect_type == "remove_random_card":
                if state.deck:
                    idx = random.randrange(len(state.deck))
                    card = state.deck.pop(idx)
                    result["effects"].append(f"Removed: {card.name_key}")

            elif effect_type == "remove_curse_cards":
                curses = [i for i, c in enumerate(state.deck) if c.card_type.value == "curse"]
                for idx in reversed(curses):
                    state.deck.pop(idx)
                result["effects"].append(f"Removed {len(curses)} curses")

            elif effect_type == "transform_card":
                if state.deck:
                    idx = random.randrange(len(state.deck))
                    pool = self.engine.get_card_pool()
                    if pool:
                        new_card = random.choice(pool)
                        state.deck[idx] = new_card
                        result["effects"].append(f"Transformed a card")

            elif effect_type == "upgrade_random_card":
                upgradable = [i for i, c in enumerate(state.deck) if not c.upgraded and c.upgraded_effects]
                if upgradable:
                    idx = random.choice(upgradable)
                    state.deck[idx].upgraded = True
                    result["effects"].append(f"Upgraded: {state.deck[idx].name_key}")

            elif effect_type == "damage":
                state.hp = max(0, state.hp - value)
                result["effects"].append(f"Took {value} damage")
                if state.hp <= 0:
                    result["death"] = True

            elif effect_type == "damage_self":
                state.hp = max(0, state.hp - value)
                result["effects"].append(f"Lost {value} HP")
                if state.hp <= 0:
                    result["death"] = True

            elif effect_type == "gain_gold":
                self.engine.add_gold(value)
                result["effects"].append(f"Gained {value} gold")

        # Set story flag if applicable
        if event.story_flag_set:
            state.story_flags.add(event.story_flag_set)

        result["message"] = choice.result_text_key
        return result

    def _check_requirements(self, choice: EventChoice) -> bool:
        """Check if player meets the requirements for a choice."""
        state = self.engine.state
        requires = choice.requires

        if not requires:
            return True

        if "gold" in requires:
            if state.gold < requires["gold"]:
                return False

        if "card_id" in requires:
            card_ids = [c.id for c in state.deck]
            if requires["card_id"] not in card_ids:
                return False

        if "relic_id" in requires:
            relic_ids = [r.id for r in state.relics]
            if requires["relic_id"] not in relic_ids:
                return False

        if "story_flag" in requires:
            if requires["story_flag"] not in state.story_flags:
                return False

        return True
