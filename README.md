# 🃏 Abyssal Codex / 深渊牌匣

> Terminal Roguelike Card Game · 终端肉鸽卡牌游戏

[English](#english) | [中文](#中文)

---

## English

**Abyssal Codex** is a roguelike deck-building game that runs entirely in your terminal. ASCII art visuals, deep strategy, and procedural generation combine for a unique adventure each run.

### Features

- **Terminal ASCII Art** — All scenes rendered with character graphics, colors, and layouts
- **4 Hero Classes** — Abyssal Knight, Shadow Weaver, Rune Sage, Bloodbinder (2 unlocked initially)
- **27+ Cards** — Attack, Skill, Power, Curse, and Legendary cards with upgrade system
- **9 Enemy Types** — Normal, Elite, and Boss enemies across 3 floors
- **10+ Relics** — Permanent passive items that shape your build
- **Keyword System** — 25+ status effects with chain reactions (Vulnerable, Poison, Charge, Dodge, Freeze...)
- **Procedural Maps** — Each floor generates unique node-based maps
- **Events & Shops** — Encounter merchants, mysterious springs, sealed chests
- **Bilingual** — Full Chinese/English support, switchable anytime
- **Meta Progression** — Earn Abyssal Memory to unlock new cards and heroes

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

### Controls

| Key | Action |
|-----|--------|
| `↑ ↓ ← →` | Navigate menus / Select cards |
| `Enter` | Confirm |
| `1-9` | Quick-select card |
| `E` | End turn (combat) |
| `D` | View deck |
| `R` | Redraw hand (with Snake Skin relic) |
| `Tab` | Switch target (combat) |
| `L` | Toggle language (main menu) |
| `ESC` | Back / Quit |

### How to Play

1. **Select a Hero** — Each has unique starting deck, HP, and core mechanics
2. **Navigate the Map** — Choose your path through combat, events, shops, and rest sites
3. **Combat** — Spend energy to play cards. Enemy intents are shown before they act
4. **Build Your Deck** — Add new cards, remove weak ones, collect relics
5. **Defeat Bosses** — Each floor ends with a boss fight; beat all 3 to win
6. **Die & Improve** — Earn Abyssal Memory to unlock more content

### Project Structure

```
Abyssal-Codex/
├── main.py              # Entry point
├── abyssal/
│   ├── engine/          # Combat, effects, AI, game loop
│   ├── data/            # Card, enemy, relic, hero dataclasses & loader
│   ├── ui/              # Terminal rendering (Rich-based)
│   ├── generator/       # Procedural generation
│   ├── content/         # Story, events, dialogue
│   ├── save/            # Save/Load system
│   └── i18n/            # Bilingual strings (zh/en)
├── data/                # JSON content databases
├── tests/               # pytest suite
└── wiki/                # Chinese wiki
```

### Tech Stack

- **Python 3.10+**
- **Rich** — Terminal rendering and styling
- **pytest** — Testing framework

---

## 中文

**深渊牌匣** 是一款完全运行在终端中的Roguelike卡牌构筑游戏。通过ASCII艺术画面、深度策略和程序化生成，带来每局独一无二的冒险体验。

### 特色

- **终端ASCII艺术** — 所有场景用字符画+颜色+布局呈现
- **4大职业** — 深渊骑士、影织者、符文贤者、血契者（初始解锁2个）
- **27+卡牌** — 攻击、技能、能力、诅咒、传说牌，支持升级
- **9种敌人** — 3层深渊中的普通、精英、Boss敌人
- **10+遗物** — 永久被动装备，塑造你的流派
- **关键词系统** — 25+种状态效果，产生化学反应（易伤、中毒、充能、闪避、冻结...）
- **程序化地图** — 每层生成独特节点式地图
- **事件与商店** — 遭遇流浪商人、神秘泉水、封印宝箱
- **双语支持** — 完整中/英文，随时切换
- **局外成长** — 获得深渊记忆，解锁新卡牌与新职业

### 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 运行游戏
python main.py
```

### 操作指南

| 按键 | 功能 |
|------|------|
| `↑ ↓ ← →` | 菜单导航 / 选牌 |
| `Enter` | 确认 |
| `1-9` | 快速选牌 |
| `E` | 结束回合（战斗） |
| `D` | 查看牌组 |
| `R` | 重抽手牌（需蛇之蜕皮遗物） |
| `Tab` | 切换目标（战斗） |
| `L` | 切换语言（主菜单） |
| `ESC` | 返回 / 退出 |

### 玩法说明

1. **选择英雄** — 每位英雄有独特的初始牌组、生命值与核心机制
2. **探索地图** — 在战斗、事件、商店、休息点之间规划路线
3. **战斗** — 消耗能量打出卡牌，敌方意图会提前展示
4. **构筑牌组** — 添加新卡，移除废牌，收集遗物
5. **击败Boss** — 每层守关Boss；通关3层即为胜利
6. **死亡与成长** — 获得深渊记忆，解锁更多内容

### 项目结构

```
Abyssal-Codex/
├── main.py              # 入口
├── abyssal/
│   ├── engine/          # 战斗、效果、AI、游戏循环
│   ├── data/            # 数据类定义与JSON加载器
│   ├── ui/              # 终端渲染（基于Rich）
│   ├── generator/       # 程序化生成
│   ├── content/         # 剧情、事件、对话
│   ├── save/            # 存档系统
│   └── i18n/            # 双语字符串（中/英）
├── data/                # JSON内容数据库
├── tests/               # pytest测试
└── wiki/                # 中文维基
```

### 技术栈

- **Python 3.10+**
- **Rich** — 终端渲染与样式
- **pytest** — 测试框架

---

## License

MIT
