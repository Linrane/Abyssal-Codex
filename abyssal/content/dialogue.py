"""Boss and NPC dialogue system."""

BOSS_DIALOGUE = {
    "sanctum_guardian": {
        "zh": {
            "intro": "「又一个灵魂...前来填补封印的空缺吗？」",
            "half_hp": "「不...我不能...让裂隙再次...扩大...」",
            "defeat": "「感谢你...让我安息...」",
        },
        "en": {
            "intro": "\"Another soul... come to fill the seal's vacancy?\"",
            "half_hp": "\"No... I cannot... let the rift... widen again...\"",
            "defeat": "\"Thank you... for letting me rest...\"",
        },
    },
    "blight_treant": {
        "zh": {
            "intro": "「深渊的根系已经深入我的躯干...你们无法阻止腐化。」",
            "half_hp": "「森林会记住...每一个倒下的灵魂...」",
            "defeat": "「终于...清净了...」",
        },
        "en": {
            "intro": "\"The abyss roots have grown deep into my trunk... you cannot stop the blight.\"",
            "half_hp": "\"The forest remembers... every fallen soul...\"",
            "defeat": "\"At last... silence...\"",
        },
    },
    "star_lord": {
        "zh": {
            "intro": "「凡人，你站在星核之上。这里的力量足以撕裂现实。」",
            "half_hp": "「有趣...你体内也流淌着虚空的回响。」",
            "defeat": "「星辰终将熄灭，而这一刻...属于你。」",
        },
        "en": {
            "intro": "\"Mortal, you stand upon the star core. This power can tear reality apart.\"",
            "half_hp": "\"Interesting... the void's echo flows through you too.\"",
            "defeat": "\"Stars must fade, and this moment... is yours.\"",
        },
    },
}


def get_boss_dialogue(boss_id: str, phase: str, lang: str = "zh") -> str:
    """Get boss dialogue for a specific phase."""
    boss = BOSS_DIALOGUE.get(boss_id, {})
    lang_data = boss.get(lang, boss.get("zh", {}))
    return lang_data.get(phase, "...")
