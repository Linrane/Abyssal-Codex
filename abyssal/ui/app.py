"""Rich-based terminal application shell with keyboard input handling.

Layout follows the framework spec (Section 12):
  Top 1/3    — Scene / Map / ASCII art + environment description
  Mid 1/3    — Enemies (left) + Status/Options (right) during combat
  Bottom 1/3 — Hand cards (horizontal, 5-8 visible)
  Bottom bar — HP / Energy / Relic icons + control hints
"""

import sys
import random
from typing import Optional, Callable

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich.style import Style
from rich import box
from abyssal.engine.game import GameEngine, RunState, RunPhase, RoomType
from abyssal.engine.combat import CombatEngine, CombatState
from abyssal.data.cards import Card, CardType
from abyssal.i18n import t

# Platform-specific keyboard input
if sys.platform == "win32":
    import msvcrt
else:
    import termios
    import tty


# ── Color Palette (framework Section 3.2) ──────────────────────────────

COLOR_ATTACK = Style(color="#FF4444")
COLOR_SKILL = Style(color="#4488FF")
COLOR_POWER = Style(color="#44FF44")
COLOR_CURSE = Style(color="#AA44FF")
COLOR_LEGENDARY = Style(color="#FFAA00")
COLOR_RARE = Style(color="#4488FF")
COLOR_EPIC = Style(color="#AA44FF")
COLOR_GOLD = Style(color="#FFDD44")
COLOR_HP_GREEN = Style(color="#44FF44")
COLOR_HP_YELLOW = Style(color="#FFCC00")
COLOR_HP_RED = Style(color="#FF4444")
COLOR_BLOCK = Style(color="#4488FF")
COLOR_ENERGY = Style(color="#FFAA00")
COLOR_GREEN = Style(color="#44FF44")
COLOR_DIM = Style(color="#8B949E")
COLOR_BRIGHT = Style(color="#E6EDF3")
COLOR_HIGHLIGHT = Style(color="#FFAA00")
COLOR_BORDER = Style(color="#30363D")
COLOR_BG = Style(bgcolor="#0D1117")

COLOR_NODE = {
    RoomType.START: Style(color="#4488FF"),
    RoomType.COMBAT: Style(color="#FF4444"),
    RoomType.ELITE: Style(color="#FF8844"),
    RoomType.SHOP: Style(color="#FFDD44"),
    RoomType.EVENT: Style(color="#44DDDD"),
    RoomType.REST: Style(color="#44FF44"),
    RoomType.BOSS: Style(color="#FF0044"),
}

CARD_TYPE_COLOR = {
    "attack": COLOR_ATTACK,
    "skill": COLOR_SKILL,
    "power": COLOR_POWER,
    "curse": COLOR_CURSE,
    "legendary": COLOR_LEGENDARY,
}


# ── Key Handler ────────────────────────────────────────────────────────

class KeyHandler:
    """Cross-platform keyboard input handler."""

    def __init__(self):
        self._win = sys.platform == "win32"

    def get_key(self) -> str:
        if self._win:
            return self._get_key_windows()
        else:
            return self._get_key_unix()

    def _get_key_windows(self) -> str:
        key = msvcrt.getch()
        if key == b'\xe0':
            key = msvcrt.getch()
            arrow_map = {b'H': 'up', b'P': 'down', b'K': 'left', b'M': 'right'}
            return arrow_map.get(key, 'unknown')
        elif key == b'\x00':
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


# ── Rendering Helpers ──────────────────────────────────────────────────

def _hp_bar(current: int, maximum: int, width: int = 12) -> str:
    """Render HP bar: ████░░░░  (framework Section 3.1)."""
    if maximum <= 0:
        return "☠ DEAD"
    pct = max(0.0, min(1.0, current / maximum))
    filled = int(width * pct)
    return "█" * filled + "░" * (width - filled)


def _hp_color(current: int, maximum: int) -> Style:
    """Color HP bar based on percentage."""
    pct = current / max(1, maximum)
    if pct > 0.6:
        return COLOR_HP_GREEN
    elif pct > 0.3:
        return COLOR_HP_YELLOW
    return COLOR_HP_RED


def _card_name(card: Card, lang: str = "zh") -> str:
    """Get localized card name with upgrade marker."""
    name = t(card.name_key, lang)
    if card.upgraded:
        name = "+" + name
    return name


def _status_icons(combatant) -> str:
    """Build status effects icon string (framework Section 5.3 keywords)."""
    icons = {
        "vulnerable": "💔", "weak": "💜", "poison": "☠",
        "charge": "⚡", "dodge": "💨", "regen": "💚",
        "thorns": "🌿", "freeze": "❄", "bloodrage": "🩸",
        "strength": "💪", "metallic": "🛡", "intangible": "👻",
        "attack": "⚔", "defense": "🛡", "gale": "🌀",
    }
    parts = []
    for name, status in combatant.statuses.items():
        if status.stacks > 0:
            icon = icons.get(name, "•")
            parts.append(f"{icon}:{status.stacks}")
    return "  ".join(parts) if parts else ""


def _intent_display(intent_type: str, value: int = 0, status: str = "", status_value: int = 0, lang: str = "zh") -> str:
    """Render enemy intent with icon + value (framework Section 6.1)."""
    icons = {"attack": "⚔", "defend": "🛡", "skill": "💀", "special": "❓"}
    icon = icons.get(intent_type, "?")
    label = t(f"intent.{intent_type}", lang)

    if intent_type == "attack":
        return f"{icon} {label} {value}"
    elif intent_type == "defend":
        return f"{icon} {label} {value}"
    elif intent_type in ("skill", "special"):
        if status:
            return f"{icon} {label}: {status} x{status_value}"
        return f"{icon} {label}"
    return f"{icon} ???"


# ── Card Widget Renderer (framework Section 3.1) ──────────────────────

def _short_desc(card: Card, lang: str) -> str:
    """Get a short single-line description for a card."""
    desc = t(card.desc_key, lang)
    effects = card.get_effects()
    args = []
    for eff in effects:
        val = getattr(eff, 'value', 0) if hasattr(eff, 'value') else eff.get('value', 0)
        etype = eff.type if hasattr(eff, 'type') else eff.get('type', '')
        if etype in ("damage", "block", "heal", "apply_status", "draw", "gain_energy"):
            args.append(str(val))
    try:
        desc = desc.format(*args)
    except (IndexError, KeyError):
        pass
    return desc


def render_hand_horizontal(hand: list[Card], lang: str, selected_idx: int, energy: int) -> str:
    """Render hand cards as Rich Table columns — CJK-safe via Rich layout."""
    if not hand:
        return ""

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1), show_edge=False)
    for _ in hand:
        table.add_column(justify="center", width=14)

    # Build 3 rows: name, cost+type, short desc
    names = []
    costs = []
    descs = []
    for i, card in enumerate(hand):
        name = _card_name(card, lang)
        if i == selected_idx:
            name = ">>" + name
        else:
            name = "  " + name
        cost = card.get_cost()
        playable = cost <= energy
        cost_mark = f"[{cost}]" if playable else f"({cost})"
        ctype = t(f"card.type.{card.card_type.value}", lang)
        cost_str = f"{cost_mark} {ctype}"
        short = _short_desc(card, lang)

        names.append(name)
        costs.append(cost_str)
        descs.append(short)

    table.add_row(*names)
    table.add_row(*costs)
    table.add_row(*descs)

    # We can't return Rich objects directly here since the caller uses console.print()
    # Return as string via console capture
    from rich.console import Console as RC
    tmp = RC(width=200)
    with tmp.capture() as capture:
        tmp.print(table)
    return capture.get().rstrip()


def render_card_mini(card: Card, lang: str = "zh", selected: bool = False, playable: bool = True) -> str:
    """Render a single card for the reward screen — compact format."""
    name = _card_name(card, lang)
    if selected:
        name = ">> " + name
    cost = card.get_cost()
    ctype = t(f"card.type.{card.card_type.value}", lang)
    short = _short_desc(card, lang)
    return f"  [{cost}] {name} ({ctype})\n     {short}"


# ── Game Application ───────────────────────────────────────────────────

class GameApp:
    """Main game application using Rich for terminal rendering.

    Layout follows framework Section 12:
      - Top: Scene / Map / ASCII art
      - Mid: Enemies (left) + Status (right) or Event choices
      - Bottom: Hand cards (horizontal)
      - Footer: HP / Energy / Relic icons + controls
    """

    def __init__(self):
        self.console = Console()
        self.engine = GameEngine(lang="zh")
        self.lang = "zh"
        self.running = True
        self.key_handler = KeyHandler()
        self.current_screen = "main_menu"
        self.screen_data: dict = {}
        self.message: str = ""
        self.message_timer: int = 0

    # ── Main Loop ────────────────────────────────────────────────────

    def run(self) -> None:
        """Main application loop."""
        self.console.clear()
        self._show_main_menu()

    # ── Helpers ──────────────────────────────────────────────────────

    def _make_menu_panel(self, options: list[tuple[str, str]], selected: int,
                         title: str = "", can_confirm: list[bool] = None) -> Panel:
        """Build a menu options panel."""
        lines = []
        for i, (key, label) in enumerate(options):
            cursor = "►" if i == selected else " "
            disabled = can_confirm and not can_confirm[i]
            if disabled:
                line = f" {cursor}  {key}. {label} {t('hint.disabled', self.lang)}"
            else:
                line = f" {cursor}  {key}. {label}"
            lines.append(line)
        content = "\n".join(lines)
        return Panel(content, title=title, border_style=COLOR_DIM, box=box.ROUNDED)

    def _confirm(self, message: str, default_no: bool = True) -> bool:
        """Anti-fool confirmation dialog. Returns True if confirmed."""
        self.console.clear()
        selected = 1 if default_no else 0  # 0=Yes, 1=No
        while True:
            self.console.clear()
            lines = [
                "",
                f"  ⚠  {message}",
                "",
            ]
            for i, label in enumerate([
                f"► {t('confirm.yes', self.lang)}" if selected == 0 else f"  {t('confirm.yes', self.lang)}",
                f"► {t('confirm.no', self.lang)}" if selected == 1 else f"  {t('confirm.no', self.lang)}",
            ]):
                lines.append(f"     {label}")
            lines.append("")
            lines.append(f"  ↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)}")

            for line in lines:
                self.console.print(line)

            key = self.key_handler.get_key()
            if key in ('up', 'down'):
                selected = 1 - selected
            elif key == 'enter':
                return selected == 0
            elif key in ('escape', 'n'):
                return False
            elif key == 'y':
                return True

    def _show_message(self, text: str):
        """Show a message panel and wait for key dismissal."""
        panel = Panel(
            Text(text, style=COLOR_BRIGHT),
            border_style=COLOR_HIGHLIGHT,
            box=box.ROUNDED,
            padding=(0, 2),
        )
        self.console.clear()
        self.console.print("")
        self.console.print(Align.center(panel))
        self.console.print("")
        self.console.print(Align.center(Text(t("misc.press_any", self.lang), style=COLOR_DIM)))
        self.key_handler.get_key()

    # ── Main Menu ────────────────────────────────────────────────────
    # Framework Section 3.1: ASCII art title, colorized, controls legend

    def _show_main_menu(self) -> None:
        self.current_screen = "main_menu"
        menu_options = [
            ("1", t("menu.new_game", self.lang)),
            ("2", t("menu.continue", self.lang)),
            ("3", t("menu.settings", self.lang)),
            ("4", t("menu.quit", self.lang)),
        ]
        selected = 0

        # Check if saves exist for Continue option
        from abyssal.save.save_manager import SaveManager
        sm = SaveManager()
        saves = sm.list_saves()
        can_confirm = [True, bool(saves), True, True]

        while self.running:
            self.console.clear()

            # Title — centered, styled
            title_text = Text()
            title_text.append("🃏  ", style=COLOR_LEGENDARY)
            title_text.append("A B Y S S A L   C O D E X", style=Style(color="#E6EDF3", bold=True))
            title_line2 = Text("深  渊  牌  匣", style=Style(color="#FFAA00", bold=True))
            subtitle = Text("Terminal Roguelike Card Game · 终端肉鸽卡牌冒险", style=COLOR_DIM)

            # Menu panel
            menu_items = []
            for i, (key, label) in enumerate(menu_options):
                cursor = "►" if i == selected else " "
                disabled_hint = ""
                if not can_confirm[i]:
                    disabled_hint = f"  [{t('menu.no_save_hint', self.lang)}]"
                menu_items.append(f" {cursor}  {key}. {label}{disabled_hint}")

            menu_panel = Panel(
                "\n".join(menu_items),
                border_style=COLOR_DIM,
                box=box.ROUNDED,
                padding=(1, 4),
            )

            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | "
                f"1-4 {t('menu.select', self.lang)} | L 中文/English | ESC {t('menu.quit', self.lang)}",
                style=COLOR_DIM,
            )
            version = Text("v0.3.0 · MIT License", style=COLOR_DIM)

            # Compose layout
            layout_lines = [
                "",
                Align.center(title_text),
                Align.center(title_line2),
                Align.center(subtitle),
                "",
                Align.center(menu_panel),
                "",
                Align.center(controls),
                "",
                Align.center(version),
            ]

            for item in layout_lines:
                if isinstance(item, str):
                    self.console.print(item)
                else:
                    self.console.print(item)

            key = self.key_handler.get_key()

            if key == 'up':
                selected = (selected - 1) % len(menu_options)
            elif key == 'down':
                selected = (selected + 1) % len(menu_options)
            elif key == 'enter':
                if not can_confirm[selected]:
                    continue
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
            elif key == '2' and can_confirm[1]:
                self._continue_game()
            elif key == '3':
                self._show_settings()
            elif key == '4':
                self.running = False
            elif key == 'l':
                self.lang = "en" if self.lang == "zh" else "zh"
                self.engine.lang = self.lang
            elif key in ('q', 'escape'):
                self.running = False

            if not self.running:
                break

    # ── Hero Select ──────────────────────────────────────────────────
    # Framework Section 4: hero cards with stats, unlock conditions

    def _show_hero_select(self) -> None:
        self.current_screen = "hero_select"
        self.engine.load_data()
        heroes = self.engine.get_unlocked_heroes()
        # Also show locked heroes (all heroes)
        all_heroes = list(self.engine._all_heroes.values())
        selected = 0

        while self.running:
            self.console.clear()
            self.console.print("")
            self.console.print(Align.center(
                Text(t("hero.select", self.lang), style=Style(bold=True, color="#E6EDF3"))
            ))
            self.console.print("")

            for i, hero in enumerate(all_heroes):
                is_selected = i == selected
                is_locked = not hero.unlocked

                border = "━" if is_selected else "─"
                top = "┏" if is_selected else "┌"
                bot = "┗" if is_selected else "└"
                cursor = "►" if is_selected else " "
                width = 46

                hero_name = t(hero.name_key, self.lang)
                hero_desc = t(hero.desc_key, self.lang)
                mechanic = t(hero.core_mechanic_key, self.lang)
                hp_str = _hp_bar(hero.max_hp, 80, 10)
                en_str = "⚡" * hero.max_energy

                if is_locked:
                    lock_info = ""
                    if hero.id == "sage":
                        lock_info = t("hero.unlock_boss", self.lang)
                    elif hero.id == "blood":
                        lock_info = t("hero.unlock_power", self.lang)
                    elif hero.id == "swordmaster":
                        lock_info = t("hero.unlock_swordmaster", self.lang)
                    lock_text = f"🔒 {t('hero.locked', self.lang)}: {lock_info}"

                lines = []
                lines.append(f"  {cursor}{top}{border * (width - 2)}{bot}")
                lines.append(f"     │ {hero_name:<{width - 2}} │")
                if is_locked:
                    lines.append(f"     │ {lock_text:<{width - 2}} │")
                else:
                    lines.append(f"     │ {hero_desc[:width - 2]:<{width - 2}} │")
                lines.append(f"     │ {t('hero.hp', self.lang)}: {hero.max_hp} {hp_str}  {t('hero.energy', self.lang)}: {en_str} │")
                lines.append(f"     │ {t('hero.mechanic', self.lang)}: {mechanic:<{width - 18}} │")
                lines.append(f"  {' ' * 1}{bot}{border * (width - 2)}{top}")

                for line in lines:
                    self.console.print(line)
                self.console.print("")

            controls = Text(
                f"←→ {t('hero.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | "
                f"1-5 {t('hero.select', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'left':
                selected = (selected - 1) % len(all_heroes)
            elif key == 'right':
                selected = (selected + 1) % len(all_heroes)
            elif key == 'up':
                selected = (selected - 1) % len(all_heroes)
            elif key == 'down':
                selected = (selected + 1) % len(all_heroes)
            elif key == 'enter':
                hero = all_heroes[selected]
                if hero.unlocked:
                    self.engine.start_run(hero.id)
                    self._show_map()
                    return
            elif key in ('escape', 'q'):
                self._show_main_menu()
                return
            elif key in (str(i) for i in range(1, len(all_heroes) + 1)):
                idx = int(key) - 1
                if idx < len(all_heroes) and all_heroes[idx].unlocked:
                    self.engine.start_run(all_heroes[idx].id)
                    self._show_map()
                    return

    # ── Map Navigation ───────────────────────────────────────────────
    # Framework Section 7: node graph with box-drawing connectors

    def _show_map(self) -> None:
        self.current_screen = "map"
        selected_avail_idx = 0  # Which available node is highlighted

        while self.running and self.engine.state and self.engine.state.phase in (RunPhase.MAP, RunPhase.COMBAT, RunPhase.EVENT, RunPhase.SHOP, RunPhase.REST):
            self.console.clear()
            state = self.engine.state
            fm = state.floor_map
            if not fm:
                break

            floor_name = t(f"floor.{state.current_floor}.name", self.lang)
            floor_effect = t(f"floor.{state.current_floor}.effect", self.lang)
            floor_desc = t(f"floor.{state.current_floor}.desc", self.lang)

            # Header panel
            header = Panel(
                f"[bold]{floor_name}[/bold]\n{floor_desc}\n[dim]{floor_effect}[/dim]",
                border_style=COLOR_NODE.get(RoomType.START, COLOR_DIM),
                box=box.ROUNDED,
            )
            self.console.print(header)

            # Status bar
            hp_bar = _hp_bar(state.hp, state.max_hp, 14)
            hp_style = _hp_color(state.hp, state.max_hp)
            status_line = Text()
            status_line.append("❤ ", style=hp_style)
            status_line.append(f"{hp_bar} {state.hp}/{state.max_hp}  ", style=hp_style)
            status_line.append(f"💰 {state.gold}  ", style=COLOR_GOLD)
            status_line.append(f"🃏 {len(state.deck)} ", style=COLOR_DIM)
            status_line.append(f"| 🏺 {len(state.relics)}", style=COLOR_DIM)
            self.console.print(Align.center(status_line))
            self.console.print("")

            # Node graph — build a Rich Table for alignment
            # Layout: nodes at col=2 (combat path) and col=4 (side path)
            available = set(self.engine.get_available_nodes())
            avail_list = sorted(available)
            if avail_list:
                selected_avail_idx = max(0, min(selected_avail_idx, len(avail_list) - 1))
            current_node_id = fm.current_node
            nodes = fm.nodes

            node_labels = {
                RoomType.START: t("map.room_start", self.lang),
                RoomType.COMBAT: t("map.room_combat", self.lang),
                RoomType.ELITE: t("map.room_elite", self.lang),
                RoomType.SHOP: t("map.room_shop", self.lang),
                RoomType.EVENT: t("map.room_event", self.lang),
                RoomType.REST: t("map.room_rest", self.lang),
                RoomType.BOSS: t("map.room_boss", self.lang),
            }

            max_row = max((n.row for n in nodes.values()), default=0)

            map_table = Table(box=None, show_header=False, padding=0, show_edge=False, show_lines=False)
            map_table.add_column(width=4)    # left indent
            map_table.add_column(width=14)   # col=2: combat path (+ start, boss)
            map_table.add_column(width=6)    # gap
            map_table.add_column(width=14)   # col=4: side path (event/shop/rest)
            map_table.add_column(width=4)    # right indent

            def render_node(node_id):
                """Build styled Text for a node, or empty Text."""
                if node_id not in nodes:
                    return Text("")
                node = nodes[node_id]
                label = node_labels.get(node.room_type, "?")
                if node.id == current_node_id:
                    t_node = Text()
                    t_node.append(">>", style=COLOR_HIGHLIGHT)
                    t_node.append(f"{label}", style=COLOR_HIGHLIGHT)
                elif node.visited:
                    t_node = Text(f"  {label}", style=COLOR_DIM)
                elif node.id in available:
                    is_sel = avail_list[selected_avail_idx] == node.id
                    st = COLOR_HIGHLIGHT if is_sel else COLOR_NODE.get(node.room_type, COLOR_BRIGHT)
                    marker = ">>" if is_sel else "  "
                    t_node = Text()
                    t_node.append(marker, style=st)
                    t_node.append(f"{label}", style=st)
                else:
                    t_node = Text(f"  {label}", style=COLOR_DIM)
                return t_node

            for row_idx in range(max_row + 1):
                row_nids = {n.col: n.id for n in nodes.values() if n.row == row_idx}
                map_table.add_row(
                    Text(""),
                    render_node(row_nids.get(2, "")),
                    Text("  "),
                    render_node(row_nids.get(4, "")),
                    Text(""),
                )
                # Connector row
                if row_idx < max_row:
                    next_nids = {n.col: n.id for n in nodes.values() if n.row == row_idx + 1}
                    def conn_cell(col_pos):
                        has_cur = col_pos in row_nids
                        has_nxt = col_pos in next_nids
                        if has_cur and has_nxt:
                            return Text("     │", style=COLOR_DIM)
                        return Text("")
                    map_table.add_row(
                        Text(""),
                        conn_cell(2),
                        Text("  "),
                        conn_cell(4),
                        Text(""),
                    )

            self.console.print(Align.center(map_table))
            self.console.print("")

            # Selection hint
            if len(avail_list) > 1:
                selected_node_id = avail_list[selected_avail_idx]
                selected_node = fm.nodes.get(selected_node_id)
                if selected_node:
                    sel_label = node_labels.get(selected_node.room_type, "?")
                    hint_text = Text()
                    hint_text.append(">> ", style=COLOR_HIGHLIGHT)
                    hint_text.append(f"{t('map.selected', self.lang)}: ", style=COLOR_BRIGHT)
                    hint_text.append(sel_label, style=COLOR_HIGHLIGHT)
                    hint_text.append(f"    ←→ {t('map.switch_node', self.lang)}    Enter {t('map.confirm_move', self.lang)}", style=COLOR_DIM)
                    self.console.print(Align.center(hint_text))
                    self.console.print("")

            # Controls
            controls = Text(
                f"←→ {t('map.switch_node', self.lang)} | Enter {t('map.confirm_move', self.lang)} | D {t('deck.title', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key in ('escape',):
                break
            elif key in ('d',):
                self._show_deck_view()
            elif key in ('left', 'right'):
                if avail_list:
                    delta = 1 if key == 'right' else -1
                    selected_avail_idx = (selected_avail_idx + delta) % len(avail_list)
            elif key in ('enter',):
                if avail_list:
                    node_id = avail_list[selected_avail_idx]
                    self.engine.move_to_node(node_id)
                    node = fm.nodes[node_id]

                    if node.room_type == RoomType.BOSS:
                        self._show_boss_intro(self.engine.state.current_floor)
                        self._show_combat()
                    elif node.room_type in (RoomType.COMBAT, RoomType.ELITE):
                        self._show_combat()
                    elif node.room_type == RoomType.EVENT:
                        self._show_event()
                    elif node.room_type == RoomType.SHOP:
                        self._show_shop()
                    elif node.room_type == RoomType.REST:
                        self._show_rest()

    def _show_boss_intro(self, floor_id: int) -> None:
        """Dramatic boss intro screen before boss combat."""
        self.console.clear()
        boss_name = t(f"enemy.{['sanctum_guardian','blight_treant','star_lord'][min(floor_id-1,2)]}", self.lang)
        intro_text = t(f"boss.intro.{min(floor_id, 3)}", self.lang)

        self.console.print("")
        self.console.print("")
        approach = Text(t("boss.approach", self.lang), style=Style(color="#FF4444", bold=True))
        self.console.print(Align.center(approach))
        self.console.print("")

        # Boss name banner
        banner = Panel(
            Text(f"👑 {boss_name}", style=Style(bold=True, color="#FFAA00")),
            border_style=COLOR_HP_RED,
            box=box.HEAVY,
        )
        self.console.print(Align.center(banner))
        self.console.print("")

        # Narrative text
        narrative = Panel(
            Text(intro_text, style=COLOR_BRIGHT),
            border_style=COLOR_DIM,
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print(Align.center(narrative))
        self.console.print("")
        self.console.print(Align.center(Text(t("misc.press_any", self.lang), style=COLOR_DIM)))

        self.key_handler.get_key()

    def _show_floor_transition(self, floor_cleared: int) -> None:
        """Narrative transition screen between floors."""
        self.console.clear()

        # Victory banner
        lines = []
        lines.append("")
        lines.append(r"  ╔══════════════════════════════════════╗")
        lines.append(rf"  ║  {t('floor.cleared', self.lang):<36s} ║")
        lines.append(r"  ╚══════════════════════════════════════╝")
        lines.append("")

        for line in lines:
            self.console.print(Align.center(line, style=COLOR_HIGHLIGHT))

        # Floor narrative
        floor_name = t(f"floor.{floor_cleared}.name", self.lang)
        self.console.print("")
        self.console.print(Align.center(Text(f"{t('floor.boss_defeated', self.lang)} — {floor_name}", style=COLOR_BRIGHT)))
        self.console.print("")

        # Transition message
        next_floor = floor_cleared + 1
        if next_floor <= 3:
            next_name = t(f"floor.{next_floor}.name", self.lang)
            next_desc = t(f"floor.{next_floor}.desc", self.lang)
            transition_text = Text()
            transition_text.append(f"\n{t('floor.transition', self.lang)}\n\n", style=COLOR_DIM)
            transition_text.append(f"{t('floor.enter_next', self.lang)}: ", style=COLOR_BRIGHT)
            transition_text.append(next_name, style=COLOR_HIGHLIGHT)
            transition_text.append("\n")
            transition_text.append(next_desc, style=COLOR_DIM)

            if next_floor == 3:
                transition_text.append(f"\n\n{t('floor.final_floor', self.lang)}", style=COLOR_HIGHLIGHT)
                transition_text.append(f"\n{t('floor.no_return', self.lang)}", style=COLOR_DIM)

            self.console.print(Align.center(transition_text))
        else:
            self.console.print(Align.center(Text(t('floor.final_floor', self.lang), style=COLOR_HIGHLIGHT)))

        self.console.print("")
        self.console.print(Align.center(Text(t("misc.press_any", self.lang), style=COLOR_DIM)))

        self.key_handler.get_key()

    # ── Combat Screen ────────────────────────────────────────────────
    # Framework Section 6, 11, 12 — THE core screen

    def _show_combat(self) -> None:
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

            # ── Top: Floor header ──
            floor_name = t(f"floor.{state.current_floor}.name", self.lang)
            header = Panel(
                f"⚔ {floor_name}    {t('combat.your_turn', self.lang)} · Turn {cs.turn}",
                border_style=COLOR_NODE[RoomType.COMBAT],
                box=box.ROUNDED,
            )
            self.console.print(header)

            # ── Mid: Enemies (framework Section 12: left, with intent) ──
            enemy_lines = []
            alive_enemies = [e for e in cs.enemies if e.alive]
            for i, enemy in enumerate(alive_enemies):
                intent_idx = [j for j, e in enumerate(cs.enemies) if e.alive][i]
                intent = combat._enemy_intents[intent_idx] if intent_idx < len(combat._enemy_intents) else None
                if intent:
                    intent_str = _intent_display(
                        intent.type.value,
                        value=intent.value,
                        status=getattr(intent, 'status', ''),
                        status_value=getattr(intent, 'status_value', 0),
                        lang=self.lang,
                    )
                else:
                    intent_str = "? ?"

                enemy_name = t(enemy.name, self.lang) if t(enemy.name, self.lang) != enemy.name else enemy.name
                hp_bar_str = _hp_bar(enemy.hp, enemy.max_hp, 12)
                target_marker = "►" if i == target_index else " "

                enemy_lines.append(
                    f"{target_marker} {intent_str:<26} │ {enemy_name}"
                )
                enemy_lines.append(
                    f"  HP: {hp_bar_str} {enemy.hp}/{enemy.max_hp}"
                )
                if enemy.block > 0:
                    enemy_lines.append(f"  🛡 Block: {enemy.block}")
                status_str = _status_icons(enemy)
                if status_str:
                    enemy_lines.append(f"  {status_str}")

            enemy_panel = Panel(
                "\n".join(enemy_lines) if enemy_lines else t("combat.victory_title", self.lang),
                title=t("combat.enemy_intent_hint", self.lang),
                border_style=COLOR_ATTACK,
                box=box.ROUNDED,
            )
            self.console.print(enemy_panel)

            # ── Mid: Player status ──
            hp_bar_str = _hp_bar(cs.player.hp, cs.player.max_hp, 14)
            hp_style = _hp_color(cs.player.hp, cs.player.max_hp)

            player_text = Text()
            player_text.append(f"⚡ {t('combat.energy', self.lang)}: {cs.energy}/{cs.max_energy}  ", style=COLOR_ENERGY)
            player_text.append("❤ ", style=hp_style)
            player_text.append(f"{hp_bar_str} {cs.player.hp}/{cs.player.max_hp}", style=hp_style)
            if cs.player.block > 0:
                player_text.append(f"\n🛡 {t('combat.block', self.lang)}: {cs.player.block}", style=COLOR_BLOCK)
            status_str = _status_icons(cs.player)
            if status_str:
                player_text.append(f"\n{status_str}")
            pile_info = t("combat.pile_info", self.lang).format(
                len(cs.draw_pile), len(cs.discard_pile), len(cs.exhaust_pile)
            )
            player_text.append(f"\n📦 {pile_info}", style=COLOR_DIM)

            player_panel = Panel(
                player_text,
                title=t("combat.your_status", self.lang),
                border_style=COLOR_SKILL,
                box=box.ROUNDED,
            )
            self.console.print(player_panel)

            # ── Bottom: Hand cards (framework Section 12) ──
            if cs.hand:
                hand_render = render_hand_horizontal(cs.hand, self.lang, selected_card, cs.energy)
                hand_panel = Panel(
                    Align.center(hand_render) if hand_render else "",
                    title=f"🃏 {t('combat.hand', self.lang)} [{len(cs.hand)}]",
                    border_style=COLOR_HIGHLIGHT if selected_card < len(cs.hand) else COLOR_DIM,
                    box=box.ROUNDED,
                )
            else:
                hand_panel = Panel(
                    Align.center(Text(t("combat.empty_hand", self.lang), style=COLOR_DIM)),
                    title=f"🃏 {t('combat.hand', self.lang)}",
                    border_style=COLOR_DIM,
                    box=box.ROUNDED,
                )
            self.console.print(hand_panel)

            # ── Controls bar ──
            controls = Text(t("combat.controls", self.lang), style=COLOR_DIM)
            self.console.print(Align.center(controls))

            # ── Combat log ──
            if cs.combat_log:
                log_text = Text()
                for log_line in cs.combat_log[-3:]:
                    log_text.append(f"  > {log_line}\n", style=COLOR_DIM)
                self.console.print(Panel(log_text, title="Log", border_style=COLOR_DIM, box=box.MINIMAL, padding=(0, 1)))

            # ── Input ──
            key = self.key_handler.get_key()

            if key == 'e':
                # Anti-fool: confirm if cards remain
                if cs.hand and cs.phase.value == "player_turn":
                    if self._confirm(t("confirm.end_turn", self.lang), default_no=True):
                        combat.end_player_turn()
                        selected_card = 0
                else:
                    combat.end_player_turn()
                    selected_card = 0
            elif key in ('r',):
                if not combat.use_snake_skin():
                    self._show_message(t("hint.need_relic", self.lang))
            elif key in ('d',):
                self._show_deck_view()
            elif key == 'tab':
                alive_indicies = [i for i, e in enumerate(cs.enemies) if e.alive]
                if alive_indicies:
                    current_pos = alive_indicies.index(target_index) if target_index in alive_indicies else 0
                    new_pos = (current_pos + 1) % len(alive_indicies)
                    target_index = alive_indicies[new_pos]
            elif key in ('up', 'left'):
                if cs.hand:
                    selected_card = (selected_card - 1) % len(cs.hand)
            elif key in ('down', 'right'):
                if cs.hand:
                    selected_card = (selected_card + 1) % len(cs.hand)
            elif key == 'enter':
                if cs.hand and selected_card < len(cs.hand):
                    card = cs.hand[selected_card]
                    if card.get_cost() <= cs.energy:
                        combat.play_card(selected_card, target_index)
                        if cs.hand:
                            selected_card = min(selected_card, len(cs.hand) - 1)
                        else:
                            selected_card = 0
            elif key in (str(i) for i in range(1, 10)):
                idx = int(key) - 1
                if idx < len(cs.hand):
                    card = cs.hand[idx]
                    if card.get_cost() <= cs.energy:
                        combat.play_card(idx, target_index)
                        if cs.hand:
                            selected_card = min(selected_card, len(cs.hand) - 1)
                        else:
                            selected_card = 0

        # ── Combat ended ──
        if combat.state.won:
            state.hp = combat.state.player.hp
            state.hp = min(state.hp, state.max_hp)

            node = self.engine.state.floor_map.nodes.get(self.engine.state.floor_map.current_node)
            was_boss = node and node.room_type == RoomType.BOSS
            if was_boss:
                state.bosses_defeated += 1
            state.encounters_completed += 1

            self._show_reward(was_boss)

            if was_boss:
                won = self.engine.complete_floor()
                if won:
                    self._show_game_over(won=True)
                    return
                else:
                    self.engine.state.phase = RunPhase.MAP
                    self._show_floor_transition(state.current_floor - 1)
                    self._show_map()
                    return
            self.engine.state.phase = RunPhase.MAP
            self._show_map()
        else:
            if combat.try_phoenix_revive():
                self._show_combat()  # Re-enter combat after revive
            else:
                state.hp = 0
                self._show_game_over(won=False)

    # ── Event Screen ─────────────────────────────────────────────────
    # Framework Section 13: ASCII art + typewriter narrative + choices

    def _show_event(self) -> None:
        event = self.engine.get_random_event()
        if not event:
            self._show_map()
            return

        from abyssal.content.event_runner import EventRunner
        runner = EventRunner(self.engine)
        event_data = runner.run_event(event)

        if event_data.get("blocked"):
            self._show_message(t("event.blocked", self.lang))
            self._show_map()
            return

        choices = event_data.get("choices", event.choices)
        selected = 0

        while self.running:
            self.console.clear()

            event_name = t(event.name_key, self.lang)
            event_desc = t(event.description_key, self.lang)

            # Header
            header = Panel(
                Text(event_name, style=Style(bold=True, color="#44DDDD")),
                border_style=Style(color="#44DDDD"),
                box=box.ROUNDED,
            )
            self.console.print(header)

            # ASCII art if available
            if event.ascii_art:
                art_panel = Panel(event.ascii_art, border_style=COLOR_DIM, box=box.MINIMAL)
                self.console.print(art_panel)

            # Description
            desc_panel = Panel(
                Text(event_desc, style=COLOR_BRIGHT),
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(desc_panel)

            # Choices
            choice_lines = []
            for i, choice in enumerate(choices):
                cursor = "►" if i == selected else " "
                choice_text = t(choice.text_key, self.lang)
                line = f" {cursor} {i + 1}. {choice_text}"

                # Show requirements (framework Section 13: gold requirements etc.)
                requires = choice.requires if hasattr(choice, 'requires') else {}
                if requires:
                    if "gold" in requires and self.engine.state.gold < requires["gold"]:
                        line += f"  [{t('event.requirement_gold', self.lang).format(requires['gold'])}]"

                # Show success chance
                if hasattr(choice, 'chance') and choice.chance < 1.0:
                    line += f"  [{t('event.chance', self.lang)}: {int(choice.chance * 100)}%]"

                choice_lines.append(line)

            choices_panel = Panel(
                "\n".join(choice_lines) if choice_lines else t("event.continue_hint", self.lang),
                title=t("event.choose", self.lang),
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(choices_panel)

            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'enter' and choices:
                choice = choices[selected]
                result = runner.execute_choice(event, choice)

                # Show result
                self.console.clear()
                result_text = t(choice.result_text_key, self.lang) if hasattr(choice, 'result_text_key') else ""
                result_panel = Panel(
                    Text(result_text, style=COLOR_BRIGHT),
                    title=t("event.encounter", self.lang),
                    border_style=COLOR_DIM,
                    box=box.ROUNDED,
                )
                self.console.print(result_panel)

                # Show effects with translation
                if result.get("effects"):
                    for eff in result["effects"]:
                        if isinstance(eff, dict):
                            eff_type = eff.get("type", "")
                            eff_value = eff.get("value", 0)
                            eff_name = eff.get("name", "")
                            # Format each effect type with i18n
                            eff_label_key = f"event.effect.{eff_type}"
                            eff_label = t(eff_label_key, self.lang)
                            if eff_label == eff_label_key:  # fallback
                                eff_label = eff_type
                            if eff_name:
                                card_name = t(eff_name, self.lang)
                                formatted = t("event.effect.with_name", self.lang).format(type=eff_label, name=card_name)
                            else:
                                formatted = t("event.effect.with_value", self.lang).format(type=eff_label, value=eff_value)
                            self.console.print(f"  → {formatted}", style=COLOR_DIM)
                        else:
                            self.console.print(f"  → {eff}", style=COLOR_DIM)

                self.console.print(Align.center(Text(
                    t("event.continue_hint", self.lang), style=COLOR_DIM
                )))

                key2 = self.key_handler.get_key()
                break
            elif key == 'up':
                selected = (selected - 1) % max(1, len(choices))
            elif key == 'down':
                selected = (selected + 1) % max(1, len(choices))
            elif key in ('escape',):
                break

        self.engine.state.phase = RunPhase.MAP
        self._show_map()

    # ── Shop Screen ──────────────────────────────────────────────────
    # Framework Section 14: cards, relics, card removal with escalating cost

    def _show_shop(self) -> None:
        self.current_screen = "shop"
        state = self.engine.state

        cards_for_sale = self.engine.generate_card_rewards(3)
        relics_for_sale = [self.engine.generate_relic_reward() for _ in range(2) if random.random() < 0.7]
        relics_for_sale = [r for r in relics_for_sale if r]
        card_prices = [50, 75, 100]
        relic_prices = [100, 150]
        remove_cost = self.engine.get_remove_cost()

        items = []
        for i, c in enumerate(cards_for_sale):
            items.append(("card", c, card_prices[min(i, len(card_prices) - 1)]))
        for i, r in enumerate(relics_for_sale):
            items.append(("relic", r, relic_prices[min(i, len(relic_prices) - 1)]))
        items.append(("remove", None, remove_cost))
        items.append(("leave", None, 0))

        selected = 0

        while self.running:
            self.console.clear()

            # Header
            gold_text = Text(f"💰 {state.gold}", style=COLOR_GOLD)
            header = Panel(
                gold_text,
                title=f"💰 {t('shop.title', self.lang)}",
                border_style=COLOR_GOLD,
                box=box.ROUNDED,
            )
            self.console.print(header)

            # Items
            item_lines = []
            for i, item in enumerate(items):
                cursor = "►" if i == selected else " "
                itype, obj, price = item
                can_afford = state.gold >= price

                if itype == "card":
                    name = _card_name(obj, self.lang)
                    ctype = t(f"card.type.{obj.card_type.value}", self.lang)
                    price_color = COLOR_GREEN if can_afford else COLOR_HP_RED
                    line = f" {cursor} 🃏 {name} ({ctype}) — {price}💰"
                elif itype == "relic":
                    name = t(obj.name_key, self.lang)
                    price_color = COLOR_GREEN if can_afford else COLOR_HP_RED
                    line = f" {cursor} 🏺 {name} — {price}💰"
                elif itype == "remove":
                    price_color = COLOR_GREEN if can_afford else COLOR_HP_RED
                    line = f" {cursor} 🗑 {t('shop.remove', self.lang)} — {price}💰"
                elif itype == "leave":
                    line = f" {cursor} 🚪 {t('shop.leave', self.lang)}"

                if not can_afford and itype != "leave":
                    line += f"  [{t('shop.no_gold', self.lang)}]"
                item_lines.append(line)

            items_panel = Panel(
                "\n".join(item_lines),
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(items_panel)

            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('shop.buy', self.lang)} | ESC {t('shop.leave', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(items)
            elif key == 'down':
                selected = (selected + 1) % len(items)
            elif key == 'enter':
                itype, obj, price = items[selected]
                if itype == "leave":
                    break
                if itype == "remove":
                    # Card removal — show deck for selection
                    removed = self._show_card_removal(price)
                    if removed:
                        # Remove item from list since removal cost increases
                        items[selected] = ("remove", None, self.engine.get_remove_cost())
                elif self.engine.spend_gold(price):
                    if itype == "card":
                        self.engine.add_card_to_deck(obj)
                        items[selected] = ("sold", None, 0)
                    elif itype == "relic":
                        self.engine.state.relics.append(obj)
                        items[selected] = ("sold", None, 0)
            elif key in ('escape',):
                break

        self.engine.state.phase = RunPhase.MAP
        self._show_map()

    def _show_card_removal(self, price: int) -> bool:
        """Show deck for card removal selection. Returns True if a card was removed."""
        state = self.engine.state
        if not state or not state.deck:
            return False

        scroll = 0
        selected = 0
        while self.running:
            self.console.clear()

            header = Panel(
                f"{t('shop.select_remove', self.lang)} — {price}💰 ({t('shop.gold', self.lang)}: {state.gold})",
                border_style=COLOR_HP_RED,
                box=box.ROUNDED,
            )
            self.console.print(header)

            cards_sorted = sorted(state.deck, key=lambda c: (c.card_type.value, c.cost))
            for i, card in enumerate(cards_sorted[scroll:scroll + 15]):
                cursor = "►" if (i + scroll) == selected else " "
                name = _card_name(card, self.lang)
                ctype = t(f"card.type.{card.card_type.value}", self.lang)
                self.console.print(f" {cursor} [{card.cost}⚡] {name} ({ctype})")

            self.console.print("")
            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'up':
                selected = max(0, selected - 1)
                if selected < scroll:
                    scroll = selected
            elif key == 'down':
                selected = min(len(cards_sorted) - 1, selected + 1)
                if selected >= scroll + 15:
                    scroll = min(selected - 14, len(cards_sorted) - 15)
            elif key == 'enter':
                if selected < len(cards_sorted):
                    if self._confirm(
                        f"{t('confirm.remove_card', self.lang)}\n\n{_card_name(cards_sorted[selected], self.lang)}",
                        default_no=True,
                    ):
                        if self.engine.spend_gold(price):
                            # Find and remove the card
                            target = cards_sorted[selected]
                            for i, c in enumerate(state.deck):
                                if c is target:
                                    self.engine.remove_card_from_deck(i)
                                    return True
                return False
            elif key in ('escape',):
                return False
        return False

    # ── Rest Screen ──────────────────────────────────────────────────
    # Framework: heal 30% OR upgrade a selected card

    def _show_rest(self) -> None:
        self.current_screen = "rest"
        state = self.engine.state
        options = ["heal", "upgrade"]
        selected = 0

        while self.running:
            self.console.clear()

            hp_bar_str = _hp_bar(state.hp, state.max_hp, 14)
            header = Panel(
                f"❤ {hp_bar_str} {state.hp}/{state.max_hp}",
                title=f"🔥 {t('rest.title', self.lang)}",
                border_style=COLOR_POWER,
                box=box.ROUNDED,
            )
            self.console.print(header)
            self.console.print("")

            for i, opt in enumerate(options):
                cursor = "►" if i == selected else " "
                if opt == "heal":
                    heal_amt = int(state.max_hp * 0.3)
                    disabled = state.hp >= state.max_hp
                    hint = f" [{t('hint.hp_full', self.lang)}]" if disabled else ""
                    self.console.print(
                        f" {cursor} 💚 {t('rest.heal', self.lang)} — {t('rest.heal_desc', self.lang)} (+{heal_amt} HP){hint}"
                    )
                elif opt == "upgrade":
                    upgradable = sum(1 for c in state.deck if not c.upgraded and (c.upgraded_effects or c.upgraded_cost > 0))
                    if upgradable == 0:
                        self.console.print(
                            f" {cursor} 🔨 {t('rest.upgrade', self.lang)} — [{t('hint.no_upgradable', self.lang)}]"
                        )
                    else:
                        self.console.print(
                            f" {cursor} 🔨 {t('rest.upgrade', self.lang)} — {t('rest.upgrade_desc', self.lang)} ({upgradable} {t('rest.upgrade_done', self.lang)})"
                        )

            self.console.print("")
            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == 'enter':
                if selected == 0:
                    if state.hp >= state.max_hp:
                        self._show_message(t("hint.hp_full", self.lang))
                        continue
                    healed = self.engine.rest_heal()
                    self._show_message(t("rest.heal_done", self.lang))
                    break
                elif selected == 1:
                    upgradable = [i for i, c in enumerate(state.deck) if not c.upgraded and (c.upgraded_effects or c.upgraded_cost > 0)]
                    if not upgradable:
                        self._show_message(t("hint.no_upgradable", self.lang))
                        continue
                    # Show selectable upgrade cards
                    self._show_upgrade_select(upgradable)
                    break
            elif key in ('escape',):
                break

        self.engine.state.phase = RunPhase.MAP
        self._show_map()

    def _show_upgrade_select(self, upgradable_indices: list[int]) -> None:
        """Show selectable cards for upgrade at rest site."""
        state = self.engine.state
        selected = 0

        def _fmt_effect(e) -> str:
            """Format a CardEffect or dict for display."""
            if isinstance(e, dict):
                etype = e.get('type', '')
                val = e.get('value', 0)
                status = e.get('status', '')
            elif hasattr(e, 'type'):
                etype = e.type
                val = e.value
                status = getattr(e, 'status', '')
            else:
                return "?"
            # Translate effect type
            type_key = f"keyword.{etype}" if etype else ""
            type_label = t(type_key, self.lang) if etype else ""
            if not type_label or type_label == type_key:
                type_label = etype
            if status:
                status_key = f"keyword.{status}"
                status_label = t(status_key, self.lang) if status_key else status
                if status_label == status_key:
                    status_label = status
                return f"{type_label} {val} [{status_label}]"
            return f"{type_label} {val}"

        while self.running:
            self.console.clear()
            header = Panel(
                t("rest.select_card_upgrade", self.lang),
                border_style=COLOR_POWER,
                box=box.ROUNDED,
            )
            self.console.print(header)
            self.console.print("")

            for i, deck_idx in enumerate(upgradable_indices):
                card = state.deck[deck_idx]
                cursor = ">>" if i == selected else "  "
                name = _card_name(card, self.lang)
                # Show before/after effects with proper formatting
                current_effects = card.get_effects()
                current_desc = ", ".join(_fmt_effect(e) for e in current_effects[:3]) if current_effects else t("keyword.none", self.lang)
                upgraded_effects = card.upgraded_effects
                upgraded_desc = ", ".join(_fmt_effect(e) for e in upgraded_effects[:3]) if upgraded_effects else "—"
                # Cost change
                cost_str = f"{card.cost}⚡"
                if card.upgraded_cost and card.upgraded_cost != card.cost:
                    cost_str += f"→{card.upgraded_cost}⚡"

                self.console.print(
                    f" {cursor} [{cost_str}] {name}"
                )
                self.console.print(f"       {t('rest.current', self.lang)}: {current_desc}", style=COLOR_DIM)
                self.console.print(f"       {t('rest.upgraded', self.lang)}: {upgraded_desc}", style=COLOR_HIGHLIGHT)
                self.console.print("")

            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'up':
                selected = (selected - 1) % len(upgradable_indices)
            elif key == 'down':
                selected = (selected + 1) % len(upgradable_indices)
            elif key == 'enter':
                self.engine.rest_upgrade(upgradable_indices[selected])
                self._show_message(t("rest.upgrade_done", self.lang))
                return
            elif key in ('escape',):
                return

    # ── Reward Screen ────────────────────────────────────────────────
    # Framework: 3 card choices with card widget rendering

    def _show_reward(self, is_boss: bool = False) -> None:
        self.current_screen = "reward"
        state = self.engine.state

        card_rewards = self.engine.generate_card_rewards(3)
        relic_reward = self.engine.generate_boss_relic() if is_boss else self.engine.generate_relic_reward()
        gold_reward = random.randint(15, 30) if not is_boss else random.randint(40, 60)
        self.engine.add_gold(gold_reward)

        selected = 0

        while self.running:
            self.console.clear()

            # Header
            header = Panel(
                Text(f"💰 +{gold_reward} {t('misc.gold', self.lang)}  |  {t('reward.card_count', self.lang).format(len(state.deck))}", style=COLOR_GOLD),
                title=f"🎁 {t('combat.rewards', self.lang)}",
                border_style=COLOR_GOLD,
                box=box.ROUNDED,
            )
            self.console.print(header)

            # Relic display
            if relic_reward:
                relic_name = t(relic_reward.name_key, self.lang)
                relic_desc = t(f"{relic_reward.name_key}.desc", self.lang)
                self.console.print(Panel(
                    f"🏺 {relic_name}\n   {relic_desc}",
                    title=t("reward.relic_get", self.lang),
                    border_style=COLOR_LEGENDARY,
                    box=box.ROUNDED,
                ))

            # Cards — render as list
            if card_rewards:
                self.console.print("")
                for i, card in enumerate(card_rewards):
                    rendered = render_card_mini(card, self.lang, selected=(i == selected), playable=True)
                    self.console.print(rendered)
                self.console.print("")

            controls = Text(
                f"←→ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | {t('reward.skip_hint', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key == 'left':
                selected = (selected - 1) % max(1, len(card_rewards))
            elif key == 'right':
                selected = (selected + 1) % max(1, len(card_rewards))
            elif key == 'up':
                selected = (selected - 1) % max(1, len(card_rewards))
            elif key == 'down':
                selected = (selected + 1) % max(1, len(card_rewards))
            elif key == 'enter' and card_rewards:
                self.engine.add_card_to_deck(card_rewards[selected])
                break
            elif key in ('s',):
                for relic in state.relics:
                    if hasattr(relic, 'on_skip_reward') and relic.on_skip_reward:
                        self.engine.add_gold(relic.on_skip_reward.get("value", 20))
                break

        if relic_reward:
            state.relics.append(relic_reward)

    # ── Deck View ────────────────────────────────────────────────────
    # Framework: categorized, colored by card type

    def _show_deck_view(self) -> None:
        state = self.engine.state
        if not state:
            return

        scroll = 0
        category = 0  # 0=All, 1=Attack, 2=Skill, 3=Power, 4=Curse
        categories = [
            ("all", None),
            ("deck.category_attack", CardType.ATTACK),
            ("deck.category_skill", CardType.SKILL),
            ("deck.category_power", CardType.POWER),
            ("deck.category_curse", CardType.CURSE),
        ]

        while self.running:
            self.console.clear()

            # Filter cards
            cat_key, cat_type = categories[category]
            if cat_type:
                filtered = [c for c in state.deck if c.card_type == cat_type]
            else:
                filtered = sorted(state.deck, key=lambda c: (c.card_type.value, c.cost))

            cat_name = t(cat_key, self.lang) if cat_key != "all" else t("deck.title", self.lang)

            # Header
            header = Panel(
                f"{len(filtered)} {t('deck.count', self.lang).format(len(filtered))}",
                title=f"🃏 {cat_name}",
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(header)

            # Cards
            visible = filtered[scroll:scroll + 18]
            for i, card in enumerate(visible):
                actual_idx = scroll + i
                name = _card_name(card, self.lang)
                ctype = t(f"card.type.{card.card_type.value}", self.lang)
                color = CARD_TYPE_COLOR.get(card.card_type.value, COLOR_BRIGHT)
                self.console.print(
                    f"  [{card.cost}⚡] {name}  [{ctype}]",
                    style=color,
                )

            if not visible:
                self.console.print(Align.center(Text(t("deck.empty", self.lang), style=COLOR_DIM)))

            self.console.print("")

            # Category tabs
            cat_line = "  ".join(
                f"{'►' if i == category else ' '} {t(c[0], self.lang)}" if c[0] != "all" else f"{'►' if i == category else ' '} ALL"
                for i, c in enumerate(categories)
            )
            self.console.print(Align.center(Text(cat_line, style=COLOR_DIM)))

            controls = Text(t("deck.controls", self.lang), style=COLOR_DIM)
            self.console.print(Align.center(controls))

            key = self.key_handler.get_key()
            if key in ('escape', 'd'):
                break
            elif key == 'up':
                scroll = max(0, scroll - 1)
            elif key == 'down':
                scroll = min(max(0, len(filtered) - 18), scroll + 1)
            elif key == 'left':
                category = (category - 1) % len(categories)
                scroll = 0
            elif key == 'right':
                category = (category + 1) % len(categories)
                scroll = 0

    # ── Game Over Screen ─────────────────────────────────────────────
    # Framework Section 9.3: ending narrative + stats + achievements

    def _show_game_over(self, won: bool = False) -> None:
        state = self.engine.state
        if not state:
            return

        memory = self.engine.calculate_memory()
        ending = self.engine.determine_ending()
        achievements = self.engine.check_achievements()

        while self.running:
            self.console.clear()

            # Victory/Death banner
            if won:
                banner = Panel(
                    Align.center(Text(t("gameover.victory", self.lang), style=Style(bold=True, color="#FFAA00"))),
                    border_style=COLOR_LEGENDARY,
                    box=box.DOUBLE,
                )
            else:
                banner = Panel(
                    Align.center(Text(t("gameover.death", self.lang), style=Style(bold=True, color="#FF4444"))),
                    border_style=COLOR_HP_RED,
                    box=box.DOUBLE,
                )
            self.console.print(banner)

            # Ending
            ending_name = t(f"ending.{ending}", self.lang)
            ending_desc = t(f"ending.{ending}.desc", self.lang)
            ending_panel = Panel(
                f"{ending_desc}",
                title=f"📜 {t('gameover.ending', self.lang)}: {ending_name}",
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(ending_panel)

            # Stats table
            stats_table = Table(box=box.MINIMAL, border_style=COLOR_DIM)
            stats_table.add_column(t("gameover.stats", self.lang), style=COLOR_DIM)
            stats_table.add_column("", style=COLOR_BRIGHT)
            stats_table.add_row(t("gameover.floors_cleared", self.lang), str(state.current_floor))
            stats_table.add_row(t("gameover.enemies_slain", self.lang), str(state.encounters_completed))
            stats_table.add_row(t("gameover.cards_collected", self.lang), str(state.cards_collected))
            stats_table.add_row(t("gameover.gold_total", self.lang), str(state.gold_total))
            stats_table.add_row(t("gameover.memory_earned", self.lang), f"💎 {memory}")
            self.console.print(Align.center(stats_table))

            # Achievements
            if achievements:
                achieve_text = Text()
                for ach_id in achievements:
                    achieve_name = t(f"achieve.{ach_id}", self.lang)
                    achieve_desc = t(f"achieve.{ach_id}.desc", self.lang)
                    achieve_text.append(f"🏆 {achieve_name}: {achieve_desc}\n", style=COLOR_LEGENDARY)
                achieve_panel = Panel(
                    achieve_text,
                    title=t("gameover.achievements", self.lang),
                    border_style=COLOR_LEGENDARY,
                    box=box.ROUNDED,
                )
                self.console.print(achieve_panel)
            else:
                self.console.print(Align.center(Text(
                    t("gameover.none", self.lang), style=COLOR_DIM
                )))

            self.console.print("")
            self.console.print(Align.center(Text(
                t("gameover.press_enter", self.lang), style=COLOR_HIGHLIGHT
            )))

            key = self.key_handler.get_key()
            if key in ('enter', 'escape'):
                self.engine.state = None
                self._show_main_menu()
                return

    # ── Settings ──────────────────────────────────────────────────────

    def _show_settings(self) -> None:
        self.current_screen = "settings"
        selected = 0
        lang_options = ["zh", "en"]

        while self.running:
            self.console.clear()

            header = Panel(
                Text(t("settings.title", self.lang), style=Style(bold=True)),
                border_style=COLOR_DIM,
                box=box.ROUNDED,
            )
            self.console.print(header)
            self.console.print("")

            for i, lopt in enumerate(lang_options):
                cursor = "►" if i == selected else " "
                label = t(f"menu.lang_{lopt}", self.lang)
                active = " ◄ " + t("settings.language", self.lang) if lopt == self.lang else ""
                self.console.print(f" {cursor} {t('settings.language', self.lang)}: {label}{active}")

            self.console.print("")
            controls = Text(
                f"↑↓ {t('menu.select', self.lang)} | Enter {t('menu.confirm', self.lang)} | ESC {t('menu.back', self.lang)}",
                style=COLOR_DIM,
            )
            self.console.print(Align.center(controls))

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

    # ── Continue Game ─────────────────────────────────────────────────

    def _continue_game(self) -> None:
        from abyssal.save.save_manager import SaveManager
        sm = SaveManager()
        saves = sm.list_saves()
        if not saves:
            self._show_message(t("save.no_save", self.lang))
            return

        data = sm.load(saves[0]["slot"])
        if data:
            self.engine.from_dict(data)
            self.lang = self.engine.state.lang
            self.engine.state.phase = RunPhase.MAP
            self._show_map()


# ── Entry Point ────────────────────────────────────────────────────────

def main():
    app = GameApp()
    app.run()


if __name__ == "__main__":
    main()
