"""Rich-based terminal application shell with keyboard input handling."""

import sys
import threading
from typing import Optional, Callable

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box

from abyssal.engine.game import GameEngine, RunState, RunPhase, RoomType
from abyssal.engine.combat import CombatEngine, CombatState
from abyssal.i18n import t

# Platform-specific keyboard input
if sys.platform == "win32":
    import msvcrt
else:
    import termios
    import tty


class KeyHandler:
    """Cross-platform keyboard input handler."""

    def __init__(self):
        self._win = sys.platform == "win32"

    def get_key(self) -> str:
        """Get a single keypress. Returns key name string."""
        if self._win:
            return self._get_key_windows()
        else:
            return self._get_key_unix()

    def _get_key_windows(self) -> str:
        key = msvcrt.getch()
        if key == b'\xe0':  # Arrow keys prefix
            key = msvcrt.getch()
            arrow_map = {b'H': 'up', b'P': 'down', b'K': 'left', b'M': 'right'}
            return arrow_map.get(key, 'unknown')
        elif key == b'\x00':  # Extended key prefix
            key = msvcrt.getch()
            return 'unknown'
        elif key == b'\r':
            return 'enter'
        elif key == b'\x1b':
            return 'escape'
        elif key == b' ':
            return 'space'
        elif key == b'\t':
            return 'tab'
        elif key == b'\x08':
            return 'backspace'
        else:
            try:
                return key.decode('utf-8').lower()
            except:
                return 'unknown'

    def _get_key_unix(self) -> str:
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
            if key == '\x1b':
                # Escape sequence
                seq = sys.stdin.read(2)
                if seq == '[':
                    k = sys.stdin.read(1)
                    arrow_map = {'A': 'up', 'B': 'down', 'C': 'right', 'D': 'left'}
                    return arrow_map.get(k, 'unknown')
                return 'escape'
            elif key == '\r':
                return 'enter'
            elif key == ' ':
                return 'space'
            elif key == '\t':
                return 'tab'
            elif key == '\x7f':
                return 'backspace'
            return key.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class GameApp:
    """Main game application using Rich for terminal rendering."""

    def __init__(self):
        self.console = Console()
        self.engine = GameEngine(lang="zh")
        self.lang = "zh"
        self.running = True
        self.key_handler = KeyHandler()

        # UI state
        self.current_screen = "main_menu"
        self.screen_data: dict = {}
        self.message: str = ""
        self.message_timer: int = 0

    def run(self) -> None:
        """Main application loop."""
        self.console.clear()
        self._show_main_menu()

    def _show_main_menu(self) -> None:
        """Display the main menu."""
        self.current_screen = "main_menu"
        menu_options = [
            ("1", t("menu.new_game", self.lang)),
            ("2", t("menu.continue", self.lang)),
            ("3", t("menu.settings", self.lang)),
            ("4", t("menu.quit", self.lang)),
        ]
        selected = 0

        while self.running:
            self.console.clear()

            # Title art
            title = t("game.title", self.lang)
            subtitle = t("game.subtitle", self.lang)

            lines = []
            lines.append("")
            lines.append("  🃏  ╔══════════════════════════════════════╗  🃏")
            lines.append(f"     ║        {title:^28} ║")
            lines.append(f"     ║     {subtitle:^30} ║")
            lines.append("     ╚══════════════════════════════════════╝")
            lines.append("")
            lines.append("          ╔══════════════════════╗")

            for i, (key, label) in enumerate(menu_options):
                cursor = "► " if i == selected else "  "
                lines.append(f"          ║ {cursor}{key}. {label:<20}║")

            lines.append("          ╚══════════════════════╝")
            lines.append("")
            lines.append(f"     🎮 ↑↓ 导航 | Enter 确认 | {t('menu.lang_zh', self.lang)}/{t('menu.lang_en', self.lang)} 切换")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()

            if key == 'up':
                selected = (selected - 1) % len(menu_options)
            elif key == 'down':
                selected = (selected + 1) % len(menu_options)
            elif key == 'enter':
                if selected == 0:
                    self._show_hero_select()
                elif selected == 1:
                    self._continue_game()
                elif selected == 2:
                    self._show_settings()
                elif selected == 3:
                    self.running = False
            elif key == '1':
                self._show_hero_select()
            elif key == '2':
                self._continue_game()
            elif key == '3':
                self._show_settings()
            elif key == '4':
                self.running = False
            elif key == 'l':
                # Quick language toggle
                self.lang = "en" if self.lang == "zh" else "zh"
                self.engine.lang = self.lang
            elif key in ('q', 'escape'):
                self.running = False

            if not self.running:
                break

    def _show_hero_select(self) -> None:
        """Hero selection screen."""
        self.current_screen = "hero_select"
        heroes = self.engine.get_unlocked_heroes()
        selected = 0

        while self.running:
            self.console.clear()

            lines = []
            lines.append(f"\n  ╔══ {t('hero.select', self.lang)} ══╗\n")

            for i, hero in enumerate(heroes):
                cursor = "► " if i == selected else "  "
                hero_name = t(hero.name_key, self.lang)
                hero_desc = t(hero.desc_key, self.lang)
                mechanic = t(hero.core_mechanic_key, self.lang)

                lines.append(f"  {cursor}┌{'─' * 38}┐")
                lines.append(f"     │ {hero_name:<36} │")
                lines.append(f"     │ {hero_desc[:36]:<36} │")
                lines.append(f"     │ {t('hero.hp', self.lang)}: {hero.max_hp:<3} {t('hero.energy', self.lang)}: {hero.max_energy:<3}  {t('hero.mechanic', self.lang)}: {mechanic:<12} │")
                lines.append(f"     └{'─' * 38}┘")
                lines.append("")

            lines.append(f"  ↑↓ {t('menu.select', self.lang)} | ESC {t('menu.back', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()

            if key == 'up':
                selected = (selected - 1) % len(heroes)
            elif key == 'down':
                selected = (selected + 1) % len(heroes)
            elif key == 'enter':
                if heroes[selected].unlocked:
                    self.engine.start_run(heroes[selected].id)
                    self._show_map()
                else:
                    self.message = "Hero not yet unlocked!"
                    self.message_timer = 5
            elif key in ('escape', 'q'):
                self._show_main_menu()
                return

    def _show_map(self) -> None:
        """Map navigation screen."""
        self.current_screen = "map"

        while self.running and self.engine.state and self.engine.state.phase == RunPhase.MAP:
            self.console.clear()
            state = self.engine.state
            fm = state.floor_map

            if not fm:
                break

            # Get floor data
            floor_name = t(f"floor.{state.current_floor}.name", self.lang)
            floor_desc = t(f"floor.{state.current_floor}.desc", self.lang)

            lines = []
            lines.append(f"\n  ╔══ {t('map.floor', self.lang)} {state.current_floor}: {floor_name} ══╗")
            lines.append(f"  ║  {floor_desc}")
            lines.append(f"  ║  {t('hp_bar', self.lang)} HP: {state.hp}/{state.max_hp}  💰 {state.gold}")
            lines.append("")

            # Render map nodes
            available = set(self.engine.get_available_nodes())
            max_row = max((n.row for n in fm.nodes.values()), default=0)

            icons = {
                RoomType.START: "🏁",
                RoomType.COMBAT: "⚔",
                RoomType.ELITE: "💀",
                RoomType.SHOP: "💰",
                RoomType.EVENT: "❓",
                RoomType.REST: "🏕",
                RoomType.BOSS: "👁",
            }

            for row in range(max_row + 1):
                row_nodes = sorted(
                    [n for n in fm.nodes.values() if n.row == row],
                    key=lambda n: n.col,
                )
                row_str = "  "
                for node in row_nodes:
                    icon = icons.get(node.room_type, "?")
                    marker = ""
                    if node.id == fm.current_node:
                        marker = "◄"
                    elif node.visited:
                        marker = "✓"
                    elif node.id in available:
                        marker = "→"
                    row_str += f" {marker}{icon} "
                lines.append(row_str)

            lines.append("")
            lines.append(f"  ↑↓←→ {t('map.navigate', self.lang)} | D {t('deck.title', self.lang)} | ESC Menu")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()

            if key in ('escape',):
                break
            elif key in ('d',):
                self._show_deck_view()
            elif key in ('up', 'down', 'left', 'right', 'enter'):
                # Pick first available node
                avail = sorted(available)
                if avail:
                    node_id = avail[0]
                    self.engine.move_to_node(node_id)
                    node = fm.nodes[node_id]

                    if node.room_type == RoomType.COMBAT or node.room_type == RoomType.ELITE or node.room_type == RoomType.BOSS:
                        self._show_combat()
                    elif node.room_type == RoomType.EVENT:
                        self._show_event()
                    elif node.room_type == RoomType.SHOP:
                        self._show_shop()
                    elif node.room_type == RoomType.REST:
                        self._show_rest()

    def _show_combat(self) -> None:
        """Combat screen."""
        self.current_screen = "combat"
        state = self.engine.state

        if not state:
            return

        enemies_def = self.engine.get_encounter_enemies()
        floor_effect = self.engine.get_floor_effect()

        combat = CombatEngine.create(
            player_hp=state.hp,
            player_max_hp=state.max_hp,
            max_energy=state.max_energy,
            deck=state.deck,
            enemy_defs=enemies_def,
            relics=state.relics,
            floor_effect=floor_effect,
        )

        selected_card = 0
        target_index = 0

        while self.running and combat.state.phase.value != "combat_end":
            cs = combat.state
            self.console.clear()

            lines = []

            # Enemy display
            lines.append("  ╔══ ENEMIES ══╗")
            alive_enemies = [e for e in cs.enemies if e.alive]
            for i, enemy in enumerate(alive_enemies):
                enemy_name = t(enemy.name, self.lang) if t(enemy.name, self.lang) != enemy.name else enemy.name
                intent_str = combat.get_enemy_intent_display(i)
                hp_bar = _simple_hp(enemy.hp, enemy.max_hp)
                target_marker = "► " if i == target_index else "  "
                lines.append(f"  {target_marker}{intent_str} {enemy_name} {hp_bar} {enemy.hp}/{enemy.max_hp}")
                if enemy.block > 0:
                    lines.append(f"     🛡 Block: {enemy.block}")

            lines.append("")

            # Player status
            lines.append(f"  ╔══ PLAYER ══╗")
            hp_bar = _simple_hp(cs.player.hp, cs.player.max_hp)
            lines.append(f"  ⚡ {cs.energy}/{cs.max_energy}  ❤ {hp_bar} {cs.player.hp}/{cs.player.max_hp}")
            if cs.player.block > 0:
                lines.append(f"  🛡 Block: {cs.player.block}")

            # Status effects
            status_str = _status_line(cs.player)
            if status_str:
                lines.append(f"  {status_str}")

            lines.append(f"  📦 Draw: {len(cs.draw_pile)} | ♻ Discard: {len(cs.discard_pile)} | 🔥 Exhaust: {len(cs.exhaust_pile)}")
            lines.append("")

            # Hand
            lines.append(f"  ╔══ {t('combat.hand', self.lang)} [{cs.turn}] ══╗")
            if cs.hand:
                for i, card in enumerate(cs.hand):
                    cursor = "► " if i == selected_card else "  "
                    cost = card.get_cost()
                    name = _get_card_name(card)
                    playable = cost <= cs.energy
                    marker = "" if playable else " [NO ENERGY]"
                    lines.append(f"  {cursor}[{i+1}] {cost}⚡ {name}{marker}")
            else:
                lines.append("  (空手)")

            lines.append("")
            lines.append(f"  [1-9] 选牌 | E {t('combat.end_turn', self.lang)} | D 牌组 | R 重抽")

            # Combat log
            if cs.combat_log:
                lines.append(f"  ---")
                for log_line in cs.combat_log[-3:]:
                    lines.append(f"  {log_line}")

            for line in lines:
                self.console.print(line)

            # Input
            key = self.key_handler.get_key()

            if key == 'e':
                combat.end_player_turn()
            elif key in ('r',):
                combat.use_snake_skin()
            elif key in ('d',):
                # Show deck view (simplified)
                pass
            elif key in ('up', 'left'):
                selected_card = (selected_card - 1) % max(1, len(cs.hand))
            elif key in ('down', 'right'):
                selected_card = (selected_card + 1) % max(1, len(cs.hand))
            elif key == 'enter':
                if cs.hand and selected_card < len(cs.hand):
                    combat.play_card(selected_card, target_index)
                    selected_card = min(selected_card, len(cs.hand) - 1) if cs.hand else 0
            elif key == 'tab':
                # Switch target
                target_index = (target_index + 1) % max(1, len(cs.enemies))
            elif key in (str(i) for i in range(1, 10)):
                idx = int(key) - 1
                if idx < len(cs.hand):
                    combat.play_card(idx, target_index)
                    selected_card = min(selected_card, len(cs.hand) - 1) if cs.hand else 0

        # Combat ended
        if combat.state.won:
            state.hp = combat.state.player.hp
            state.hp = min(state.hp, state.max_hp)

            # Floor 3 boss defeated = victory
            was_boss = self.engine.state.floor_map.nodes[self.engine.state.floor_map.current_node].room_type == RoomType.BOSS
            state.bosses_defeated += 1 if was_boss else 0
            state.encounters_completed += 1

            # Generate rewards
            self.engine.state = state  # Sync back
            self._show_reward(was_boss)

            if was_boss:
                won = self.engine.complete_floor()
                if won:
                    self._show_game_over(won=True)
                    return
                else:
                    self._show_map()
                    return
            self._show_map()
        else:
            # Check phoenix feather
            if combat.try_phoenix_revive():
                # Continue combat
                pass
            else:
                state.hp = 0
                self._show_game_over(won=False)

    def _show_reward(self, is_boss: bool = False) -> None:
        """Reward screen after combat."""
        self.current_screen = "reward"
        state = self.engine.state

        # Generate rewards
        card_rewards = self.engine.generate_card_rewards(3)
        relic_reward = self.engine.generate_boss_relic() if is_boss else self.engine.generate_relic_reward()
        gold_reward = random.randint(15, 30) if not is_boss else random.randint(40, 60)
        self.engine.add_gold(gold_reward)

        selected = 0

        while self.running:
            self.console.clear()
            lines = []
            lines.append(f"\n  ╔══ {t('combat.rewards', self.lang)} ══╗")
            lines.append(f"  💰 +{gold_reward} {t('misc.gold', self.lang)} (Total: {state.gold})")
            lines.append("")

            if card_rewards:
                lines.append(f"  {t('reward.card_select', self.lang)}:")
                for i, card in enumerate(card_rewards):
                    cursor = "► " if i == selected else "  "
                    name = _get_card_name(card)
                    lines.append(f"  {cursor}{name} ({card.cost}⚡)")
                lines.append("")

            if relic_reward:
                relic_name = t(relic_reward.name_key, self.lang)
                lines.append(f"  🏺 {t('reward.relic_get', self.lang)}: {relic_name}")

            lines.append(f"  Enter {t('menu.select', self.lang)} | S {t('combat.skip', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key == 'enter' and card_rewards:
                self.engine.add_card_to_deck(card_rewards[selected])
                break
            elif key in ('s',):
                # Skip card - Broken Crown check
                for relic in state.relics:
                    if relic.on_skip_reward:
                        self.engine.add_gold(relic.on_skip_reward.get("value", 20))
                break
            elif key == 'up':
                selected = (selected - 1) % len(card_rewards) if card_rewards else 0
            elif key == 'down':
                selected = (selected + 1) % len(card_rewards) if card_rewards else 0

        if relic_reward:
            state.relics.append(relic_reward)

    def _show_event(self) -> None:
        """Event screen."""
        event = self.engine.get_random_event()
        if not event:
            self._show_map()
            return

        self.current_screen = "event"
        selected = 0

        while self.running:
            self.console.clear()
            lines = []

            event_name = t(event.name_key, self.lang)
            event_desc = t(event.description_key, self.lang)

            lines.append(f"\n  ╔══ {t('event.encounter', self.lang)}: {event_name} ══╗")
            lines.append(f"  {event_desc}")
            lines.append("")

            if event.ascii_art:
                lines.append(event.ascii_art)
                lines.append("")

            for i, choice in enumerate(event.choices):
                cursor = "► " if i == selected else "  "
                choice_text = t(choice.text_key, self.lang)
                lines.append(f"  {cursor}{i+1}. {choice_text}")

            lines.append(f"  Enter {t('event.choose', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key == 'enter' and event.choices:
                choice = event.choices[selected]
                # Apply effects (simplified)
                for effect in choice.effects:
                    etype = effect.get("type", "")
                    if etype == "heal_percent":
                        heal_amt = int(self.engine.state.max_hp * effect.get("value", 0.25))
                        self.engine.state.hp = min(self.engine.state.max_hp, self.engine.state.hp + heal_amt)
                    elif etype == "add_random_relic":
                        relic = self.engine.generate_relic_reward()
                        if relic:
                            self.engine.state.relics.append(relic)
                    elif etype == "remove_gold":
                        self.engine.spend_gold(effect.get("value", 0))
                break
            elif key == 'up':
                selected = (selected - 1) % len(event.choices) if event.choices else 0
            elif key == 'down':
                selected = (selected + 1) % len(event.choices) if event.choices else 0

        self._show_map()

    def _show_shop(self) -> None:
        """Shop screen."""
        self.current_screen = "shop"

        # Generate shop inventory
        cards_for_sale = self.engine.generate_card_rewards(3)
        relics_for_sale = [self.engine.generate_relic_reward() for _ in range(2) if random.random() < 0.7]

        card_prices = [50, 75, 100]
        relic_prices = [100, 150]
        remove_cost = self.engine.get_remove_cost()

        selected = 0
        items = [
            *[("card", c, card_prices[min(i, len(card_prices)-1)]) for i, c in enumerate(cards_for_sale)],
            *[("relic", r, relic_prices[min(i, len(relic_prices)-1)]) for i, r in enumerate(relics_for_sale) if r],
            ("remove", None, remove_cost),
            ("leave", None, 0),
        ]

        while self.running:
            self.console.clear()
            state = self.engine.state
            lines = []
            lines.append(f"\n  ╔══ {t('shop.title', self.lang)} ══╗")
            lines.append(f"  💰 {t('shop.gold', self.lang)}: {state.gold}")
            lines.append("")

            for i, item in enumerate(items):
                cursor = "► " if i == selected else "  "
                itype, obj, price = item
                if itype == "card":
                    name = _get_card_name(obj)
                    lines.append(f"  {cursor}🃏 {name} - {price}💰")
                elif itype == "relic":
                    name = t(obj.name_key, self.lang)
                    lines.append(f"  {cursor}🏺 {name} - {price}💰")
                elif itype == "remove":
                    lines.append(f"  {cursor}🗑 {t('shop.remove', self.lang)} - {price}💰")
                elif itype == "leave":
                    lines.append(f"  {cursor}🚪 {t('shop.leave', self.lang)}")

            lines.append(f"  Enter {t('shop.buy', self.lang)} | ESC {t('shop.leave', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(items)
            elif key == 'down':
                selected = (selected + 1) % len(items)
            elif key == 'enter':
                itype, obj, price = items[selected]
                if itype == "leave":
                    break
                if self.engine.spend_gold(price):
                    if itype == "card":
                        self.engine.add_card_to_deck(obj)
                    elif itype == "relic":
                        self.engine.state.relics.append(obj)
                    elif itype == "remove":
                        # TODO: Show deck for selection
                        pass
            elif key in ('escape',):
                break

        self._show_map()

    def _show_rest(self) -> None:
        """Rest site screen."""
        self.current_screen = "rest"
        selected = 0
        options = ["heal", "upgrade"]
        state = self.engine.state

        while self.running:
            self.console.clear()
            lines = []
            lines.append(f"\n  ╔══ {t('rest.title', self.lang)} ══╗")
            lines.append(f"  HP: {state.hp}/{state.max_hp}")
            lines.append("")

            for i, opt in enumerate(options):
                cursor = "► " if i == selected else "  "
                if opt == "heal":
                    lines.append(f"  {cursor}💚 {t('rest.heal', self.lang)} - {t('rest.heal_desc', self.lang)}")
                elif opt == "upgrade":
                    lines.append(f"  {cursor}🔨 {t('rest.upgrade', self.lang)} - {t('rest.upgrade_desc', self.lang)}")
            lines.append(f"  Enter {t('menu.select', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == 'enter':
                if selected == 0:
                    if state.hp < state.max_hp:
                        healed = self.engine.rest_heal()
                        self.message = t('rest.heal_done', self.lang)
                    else:
                        self.message = t('rest.max_hp', self.lang)
                elif selected == 1:
                    # Simplified: upgrade first upgradable card
                    for i, card in enumerate(state.deck):
                        if not card.upgraded and card.upgraded_effects:
                            self.engine.rest_upgrade(i)
                            break
                break
            elif key in ('escape',):
                break

        self._show_map()

    def _show_deck_view(self) -> None:
        """Deck view screen."""
        state = self.engine.state
        if not state:
            return

        scroll = 0
        while self.running:
            self.console.clear()
            lines = []
            lines.append(f"\n  ╔══ {t('deck.title', self.lang)}: {len(state.deck)} {t('deck.count', self.lang).format(len(state.deck))} ══╗")
            lines.append("")

            sorted_deck = sorted(state.deck, key=lambda c: (c.card_type.value, c.cost))

            for i, card in enumerate(sorted_deck[scroll:scroll+20]):
                name = _get_card_name(card)
                type_str = t(f"card.type.{card.card_type.value}", self.lang)
                lines.append(f"  [{card.cost}⚡] {name} ({type_str})")

            lines.append(f"  ↑↓ Scroll | ESC {t('menu.back', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key in ('escape', 'd'):
                break
            elif key == 'up':
                scroll = max(0, scroll - 1)
            elif key == 'down':
                scroll = min(max(0, len(state.deck) - 20), scroll + 1)

    def _show_game_over(self, won: bool = False) -> None:
        """Game over screen."""
        state = self.engine.state
        if not state:
            return

        memory = self.engine.calculate_memory()

        while self.running:
            self.console.clear()
            lines = []

            if won:
                lines.append(f"\n  ╔══ {t('gameover.victory', self.lang)} ══╗")
            else:
                lines.append(f"\n  ╔══ {t('gameover.death', self.lang)} ══╗")

            lines.append("")
            lines.append(f"  {t('gameover.memory_earned', self.lang)}: {memory} 💎")
            lines.append("")
            lines.append(f"  {t('gameover.stats', self.lang)}:")
            lines.append(f"  {t('gameover.floors_cleared', self.lang)}: {state.current_floor}")
            lines.append(f"  {t('gameover.enemies_slain', self.lang)}: {state.encounters_completed}")
            lines.append(f"  {t('gameover.cards_collected', self.lang)}: {state.cards_collected}")
            lines.append(f"  {t('gameover.gold_total', self.lang)}: {state.gold_total}")
            lines.append("")
            lines.append(f"  Enter {t('gameover.return', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key in ('enter', 'escape'):
                self.engine.state = None
                self._show_main_menu()
                return

    def _show_settings(self) -> None:
        """Settings screen."""
        self.current_screen = "settings"
        selected = 0
        lang_options = ["zh", "en"]

        while self.running:
            self.console.clear()
            lines = []
            lines.append(f"\n  ╔══ {t('settings.title', self.lang)} ══╗")
            lines.append("")

            for i, lopt in enumerate(lang_options):
                cursor = "► " if i == selected else "  "
                label = t(f"menu.lang_{lopt}", self.lang)
                active = " ◄" if lopt == self.lang else ""
                lines.append(f"  {cursor}{t('settings.language', self.lang)}: {label}{active}")

            lines.append(f"  Enter {t('menu.select', self.lang)} | ESC {t('menu.back', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(lang_options)
            elif key == 'down':
                selected = (selected + 1) % len(lang_options)
            elif key == 'enter':
                self.lang = lang_options[selected]
                self.engine.lang = self.lang
            elif key in ('escape',):
                self._show_main_menu()
                return

    def _continue_game(self) -> None:
        """Continue from a save."""
        from abyssal.save.save_manager import SaveManager
        sm = SaveManager()
        saves = sm.list_saves()
        if not saves:
            self.message = t("save.no_save", self.lang)
            return
        # Load latest save
        data = sm.load(saves[0]["slot"])
        if data:
            self.engine.from_dict(data)
            self.lang = self.engine.state.lang
            self._show_map()


def _simple_hp(current: int, maximum: int, width: int = 10) -> str:
    """Simple HP bar string."""
    if maximum <= 0:
        return "☠"
    pct = max(0, min(1.0, current / maximum))
    filled = int(width * pct)
    return "█" * filled + "░" * (width - filled)


def _get_card_name(card) -> str:
    from abyssal.i18n import t
    name = t(card.name_key, "zh")
    if card.upgraded:
        name = "+" + name
    return name


def _status_line(combatant) -> str:
    """Get a status effects line."""
    icons = {
        "vulnerable": "💔", "weak": "💜", "poison": "☠",
        "charge": "⚡", "dodge": "💨", "regen": "💚",
        "thorns": "🌿", "freeze": "❄", "bloodrage": "🩸",
        "attack": "⚔", "defense": "🛡", "gale": "🌀",
    }
    parts = []
    for name, status in combatant.statuses.items():
        if status.stacks > 0:
            icon = icons.get(name, "•")
            parts.append(f"{icon}:{status.stacks}")
    return " ".join(parts)


# Need to import random for reward generation
import random
