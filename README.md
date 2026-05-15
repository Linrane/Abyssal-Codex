<div align="center">

![version](https://img.shields.io/badge/version-0.4.2-8b5cf6?style=flat-square)
![python](https://img.shields.io/badge/python-3.10+-3b82f6?style=flat-square)
![license](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)
![tests](https://img.shields.io/badge/tests-62_passed-22c55e?style=flat-square)
![i18n](https://img.shields.io/badge/i18n-中文_|_English-f59e0b?style=flat-square)

</div>

<br>

<h1 align="center">
  🃏 Abyssal Codex<br>
  <sub>深渊牌匣</sub>
</h1>

<p align="center"><strong>Terminal Roguelike Card Game · 终端肉鸽卡牌冒险</strong></p>

<p align="center">
  <a href="https://github.com/Linrane/Abyssal-Codex/wiki">📖 Wiki</a>
  ·
  <a href="#-quick-start--快速开始">🚀 Quick Start</a>
  ·
  <a href="#-features--游戏特色">✨ Features</a>
  ·
  <a href="#-controls--操作指南">🎮 Controls</a>
  ·
  <a href="#-heroes--英雄">🦸 Heroes</a>
  ·
  <a href="#-story--剧情">📜 Story</a>
</p>

---

> *"The seal was never meant to keep the Abyss out. It was meant to keep us in."*
>
> *"封印从来不是为了阻挡深渊。而是为了困住我们。"*

**Abyssal Codex** is a terminal roguelike card game built with Python and Rich. Each run descends through three procedurally generated floors — draft cards, collect relics, face branching events, and uncover the truth behind the ancient seal.

**深渊牌匣**是一款基于 Python + Rich 的终端肉鸽卡牌游戏。每一局穿越三层程序生成的地图，构筑牌组、收集遗物、应对分支事件，揭开远古封印背后的真相。

---

## 🚀 Quick Start / 快速开始

```bash
git clone git@github.com:Linrane/Abyssal-Codex.git
cd Abyssal-Codex
pip install -r requirements.txt
python main.py
```

**Requirements:** Python 3.10+ · [`rich>=13.0.0`](https://github.com/Textualize/rich)

---

## ✨ Features / 游戏特色

| | |
|---|---|
| 🎴 **75 Cards** 卡牌 | Attack · Skill · Power · Curse · Legendary — each upgradeable with card art |
| 👹 **15 Enemies** 敌人 | Normal · Elite · Boss across 3 themed floors, with intent display & phase mechanics |
| 💎 **26 Relics** 遗物 | Common · Boss · Legendary · Curse tiers with passive & trigger effects |
| 📜 **18 Events** 事件 | Story-driven branching, class-specific encounters, typewriter narrative |
| 🦸 **5 Heroes** 英雄 | 2 unlocked initially, 3 unlockable through meta-progression |
| 🔑 **15 Keywords** 关键词 | Vulnerable · Weak · Poison · Charge · Dodge · Regen · Thorns · Freeze · Resonance · Bloodrage · Strength · Metallic · Intangible · Armor Break · Stances |
| 🗺️ **Procedural Maps** 程序化地图 | Node graph with box-drawing connectors, combat/elite/shop/event/rest/boss |
| 🏁 **5 Endings** 结局 | Reseal · Deicide · Liberation · Consumption · Resignation — shaped by your choices |
| 🏆 **14 Achievements** 成就 | Floor clears · hero wins · deck challenges · wealth · relic hunting · ending-based |
| 🎨 **Rich UI** 界面 | Panel-based layout, card widgets, color-coded types, anti-fool confirmations |
| 💾 **Save System** 存档 | 3-slot SQLite persistence with mid-run resume |
| 🌐 **Bilingual** 双语 | ~590 strings in Chinese & English, switchable at any time (L key) |
| ⚡ **Meta Progression** 局外成长 | Earn Abyssal Memory to unlock heroes, cards, and relics |

---

## 🎮 Controls / 操作指南

| Key 按键 | Action 功能 |
|:---:|---|
| `↑ ↓ ← →` | Navigate menus / Select cards / Switch map nodes 导航/选牌/切换地图节点 |
| `Enter` | Confirm selection 确认 |
| `1`–`9` | Quick-select card 快速选牌 |
| `E` | End turn 结束回合 (confirms if cards remain) |
| `D` | Open deck viewer 查看牌组 (categorized by type) |
| `Tab` | Switch target 切换目标 |
| `R` | Redraw hand 重抽手牌 *(needs Snake Skin)* |
| `L` | Toggle language 切换语言 *(main menu)* |
| `S` | Skip card reward 跳过卡牌奖励 |
| `ESC` | Back / Quit 返回/退出 |

---

## 🦸 Heroes / 英雄

| Hero 英雄 | HP | ⚡ | Core Mechanic 核心机制 | Unlock 解锁 |
|---|---|---|---|---|
| **Abyssal Knight** 深渊骑士 | 80 | 3 | Vulnerable + Armor Break 易伤破甲 | 初始 |
| **Shadow Weaver** 影织者 | 65 | 3 | Poison + Dodge 中毒闪避 | 初始 |
| **Rune Sage** 符文贤者 | 60 | 4 | Charge + Resonance 充能共鸣 | 击败10个Boss |
| **Bloodbinder** 血契者 | 55 | 3 | Bloodrage — lower HP = higher damage 血怒 | 单局使用20次能力牌 |
| **Wandering Swordmaster** 流浪剑豪 | 70 | 3 | Stance switching 架势切换 | 隐藏职业 |

---

## 📜 Story / 剧情

You descend into the Abyss seeking to repair the ancient seal — but fragments of truth suggest the seal was never broken by accident. Twelve previous heroes are trapped within. An Old God watches from beyond the rift. And the Church may not be what it claims.

你深入深渊修复封印——但碎片化的真相暗示封印从来不是意外崩坏的。十二位前代英雄的灵魂被困其中。旧神在裂隙之外注视。而教会……

**Five paths. One descent.** / **五条道路。一次降临。**

---

## 🗺️ Floors / 深渊层

| Floor | Name | Effect |
|---|---|---|
| 1 | **Crumbling Sanctuary** 崩塌圣堂 | Both sides start combat with 1 Vulnerable |
| 2 | **Gloomwood** 幽暗密林 | From turn 3 onward, everyone gains 1 Poison per turn |
| 3 | **Star Core Rift** 星核裂隙 | +1 Energy/turn, card costs fluctuate ±1 |

---

## 📂 Project Structure / 项目结构

```
Abyssal-Codex/
├── main.py                    # Entry point 入口
├── requirements.txt           # rich, pytest
├── abyssal/
│   ├── engine/                # Combat, effects, AI, game loop
│   ├── data/                  # Dataclasses + JSON loader
│   ├── ui/                    # Terminal UI (Rich-based)
│   ├── generator/             # Procedural map/reward generation
│   ├── content/               # Story flags, event runner
│   ├── save/                  # SQLite persistence
│   └── i18n/                  # 548 bilingual strings (zh/en)
├── data/                      # JSON content databases
│   ├── cards/                 # 73 cards (core, class, legendary, curse)
│   ├── enemies/               # 15 enemies across 3 floors
│   ├── relics/                # 26 relics (common + special)
│   └── events/                # 18 events with branching
└── tests/                     # 62 pytest cases
```

---

## 🧪 Testing / 测试

```bash
pytest tests/ -v          # 62 tests, all passing
pytest tests/ --cov=abyssal  # with coverage
```

---

## 📖 Wiki / 维基

Full documentation is on the **[GitHub Wiki](https://github.com/Linrane/Abyssal-Codex/wiki)** — hero guides, card catalog, enemy compendium, relic reference, event walkthroughs, keyword mechanics, ending conditions, and strategy tips.

完整文档见 **[GitHub Wiki](https://github.com/Linrane/Abyssal-Codex/wiki)** —— 英雄攻略、卡牌目录、敌人图鉴、遗物参考、事件详解、关键词机制、结局条件、策略技巧。

---

<p align="center">
  <samp>v0.4.2 · <a href="https://github.com/Linrane/Abyssal-Codex/issues">Issues</a> · <a href="https://github.com/Linrane/Abyssal-Codex/wiki">Wiki</a> · MIT License</samp>
</p>
