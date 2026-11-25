"""Deterministic prose-risk audit for Chinese fiction.

The audit does not judge literary quality. It surfaces recurring signals that
often correlate with template-like prose: generic atmosphere, over-explanation,
decorative metaphor density, uniform syntax, repeated openings, and stock
emotion/body inventories.
"""

from __future__ import annotations

from collections import Counter
import json
import math
import re
from typing import Any

CJK_RE = re.compile(r"[\u3400-\u9fff]")
VISIBLE_RE = re.compile(r"[\u3400-\u9fffA-Za-z0-9]")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[。！？!?])\s*")
DIALOGUE_RE = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』|\"[^\"\\n]*\"")

GENERIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "空气凝固/静止": re.compile(r"空气.{0,4}(?:仿佛|像是|好像)?(?:凝固|凝滞|静止)"),
    "时间静止": re.compile(r"时间.{0,4}(?:仿佛|像是|好像)?(?:静止|停住|凝固)"),
    "某种说不清": re.compile(r"某种.{0,8}(?:情绪|感觉|东西|力量|变化)|说不清(?:道不明)?"),
    "心里某处": re.compile(r"心里某处|心底某处"),
    "整个世界": re.compile(r"(?:仿佛|好像|像是).{0,6}整个世界"),
    "不知过了多久": re.compile(r"不知(?:道)?过了多久"),
    "终于明白": re.compile(r"终于(?:明白|意识到|懂得)"),
    "这一刻/那一刻": re.compile(r"这一刻|那一刻"),
    "从这一刻起": re.compile(r"从这一刻起|从那一刻起"),
    "这意味着": re.compile(r"(?:这|那)意味着"),
    "既又": re.compile(r"既.{0,14}又"),
}

EXPLANATION_PATTERNS: dict[str, re.Pattern[str]] = {
    "原来": re.compile(r"原来[，,。]"),
    "她知道/他明白": re.compile(r"[她他]知道[，,]|[她他]明白[，,]"),
    "仿佛在提醒": re.compile(r"(?:仿佛|像是).{0,8}(?:提醒|宣告|证明|诉说)"),
    "因为所以": re.compile(r"因为.{0,16}所以|之所以.{0,20}是因为"),
    "像是要": re.compile(r"(?:仿佛|好像|像是)要.{0,12}(?:吞没|撕裂|击碎|点燃)"),
}

AI_ELEVATION_PATTERNS: dict[str, re.Pattern[str]] = {
    "命运/宿命升华": re.compile(r"命运(?:的)?齿轮|宿命感|命中注定|难逃宿命"),
    "从此改变": re.compile(r"从此(?:改变|不同|不再一样)|一切(?:都)?不一样了"),
    "解释性尾句": re.compile(r"(?:仿佛|好像|像是|似乎).{0,10}(?:诉说|宣告|提醒|昭示|预示|证明|意味着)"),
    "否定式排比": re.compile(r"不只是.{0,24}(?:更是|而是)|不仅是.{0,24}(?:更是|还是)|不是.{0,24}而是"),
    "三项排比": re.compile(r"[\u3400-\u9fff]{1,10}、[\u3400-\u9fff]{1,10}、[\u3400-\u9fff]{1,10}"),
}

PURPLE_PROSE_RE = re.compile(
    r"不可方物|惊心动魄的美|致命(?:的)?诱惑|美得惊心动魄|勾魂摄魄|活色生香|摄人心魄"
)
ABSTRACT_NOUN_RE = re.compile(
    r"张力|底色|褶皱|容器|边界|隐喻|宿命感|破碎感|救赎感|荒芜感|疏离感"
)
DASH_RE = re.compile(r"——|—")
PROP_EXPOSITION_RE = re.compile(
    r"(?:上面|墙上|门上|牌子上|告示上|屏幕上|手机上|纸上).{0,4}(?:写|显示|印)着"
)
STAGE_ACTION_RE = re.compile(
    r"点头|拿起|指了|转身|推门|走过去|停下|抬头|低头|伸手|放下|站起|坐下|看过去"
)
TRANSLATIONESE_RE = re.compile(r"顺着.{0,8}方向看过去|映入眼帘|映入眼中|目光落在")

METAPHOR_RE = re.compile(r"仿佛|像是|如同|宛如|好似|犹如|恍若|像(?!片|素|样|册|机)")
EMOTION_RE = re.compile(
    r"羞耻|慌乱|心动|情欲|欲望|爱意|恐惧|兴奋|满足|空虚|绝望|快感|"
    r"复杂|微妙|暧昧|温柔|心疼|委屈|愤怒"
)
BODY_INVENTORY_RE = re.compile(
    r"心跳加速|呼吸急促|浑身发烫|头脑一片空白|双腿发软|"
    r"脚趾蜷缩|眼前发白|浑身战栗|身体一颤|喉咙发紧"
)
ADVERBIAL_RE = re.compile(r"[\u3400-\u9fff]地")
PRONOUN_START = ("她", "他", "我", "它", "你")


def _visible_len(text: str) -> int:
    return len(VISIBLE_RE.findall(text))


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def _p90(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, math.ceil(len(ordered) * 0.9) - 1)
    return ordered[idx]


def _stdev(values: list[int]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _per_1000(count: int, char_count: int) -> float:
    return round(count * 1000 / max(char_count, 1), 2)


def _matches(patterns: dict[str, re.Pattern[str]], text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label, pattern in patterns.items():
        count = len(pattern.findall(text))
        if count:
            counts[label] = count
    return counts


def _sentence_stats(sentences: list[str]) -> dict[str, float | int]:
    lengths = [_visible_len(s) for s in sentences]
    lengths = [n for n in lengths if n > 0]
    if not lengths:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "p90": 0,
            "stdev": 0.0,
            "short_ratio": 0.0,
            "long_ratio": 0.0,
        }
    return {
        "count": len(lengths),
        "mean": round(sum(lengths) / len(lengths), 1),
        "median": round(_median(lengths), 1),
        "p90": _p90(lengths),
        "stdev": round(_stdev(lengths), 1),
        "short_ratio": round(sum(n < 12 for n in lengths) / len(lengths), 3),
        "long_ratio": round(sum(n > 45 for n in lengths) / len(lengths), 3),
    }


def _top_ngrams(text: str, n: int = 4, limit: int = 8) -> list[tuple[str, int]]:
    sequence = "".join(CJK_RE.findall(text))
    counts = Counter(sequence[i : i + n] for i in range(max(0, len(sequence) - n + 1)))
    filtered = [
        (gram, count)
        for gram, count in counts.items()
        if count >= 3 and len(set(gram)) >= 3
    ]
    filtered.sort(key=lambda item: (-item[1], item[0]))
    return filtered[:limit]


def audit_text(text: str) -> dict[str, Any]:
    """Return a JSON-serializable prose-risk report."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    dialogue_blocks = DIALOGUE_RE.findall(text)
    dialogue_chars = sum(len(VISIBLE_RE.findall(block)) for block in dialogue_blocks)
    narrative_text = DIALOGUE_RE.sub("", text)

    char_count = _visible_len(text)
    narrative_chars = _visible_len(narrative_text)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(text) if _visible_len(s)]
    narrative_sentences = [
        s.strip() for s in SENTENCE_SPLIT_RE.split(narrative_text) if _visible_len(s)
    ]

    paragraph_lengths = [_visible_len(p) for p in paragraphs]
    short_beat_run = 0
    current_beat_run = 0
    for paragraph in paragraphs:
        narrative_paragraph = DIALOGUE_RE.sub("", paragraph).strip()
        paragraph_sentences = [
            part
            for part in SENTENCE_SPLIT_RE.split(narrative_paragraph)
            if _visible_len(part)
        ]
        is_fake_beat = (
            2 <= _visible_len(narrative_paragraph) <= 14
            and len(paragraph_sentences) == 1
            and not DIALOGUE_RE.search(paragraph)
        )
        current_beat_run = current_beat_run + 1 if is_fake_beat else 0
        short_beat_run = max(short_beat_run, current_beat_run)
    paragraph_stats = {
        "count": len(paragraph_lengths),
        "mean": round(sum(paragraph_lengths) / max(len(paragraph_lengths), 1), 1),
        "stdev": round(_stdev(paragraph_lengths), 1),
        "one_sentence_ratio": round(
            sum(len([s for s in SENTENCE_SPLIT_RE.split(p) if _visible_len(s)]) == 1 for p in paragraphs)
            / max(len(paragraphs), 1),
            3,
        ),
    }

    generic_hits = _matches(GENERIC_PATTERNS, narrative_text)
    explanation_hits = _matches(EXPLANATION_PATTERNS, narrative_text)
    elevation_hits = _matches(AI_ELEVATION_PATTERNS, narrative_text)
    metaphor_count = len(METAPHOR_RE.findall(narrative_text))
    emotion_count = len(EMOTION_RE.findall(narrative_text))
    body_inventory_count = len(BODY_INVENTORY_RE.findall(text))
    purple_count = len(PURPLE_PROSE_RE.findall(narrative_text))
    abstract_noun_count = len(ABSTRACT_NOUN_RE.findall(narrative_text))
    dash_count = len(DASH_RE.findall(text))
    prop_exposition_count = len(PROP_EXPOSITION_RE.findall(text))
    translationese_count = len(TRANSLATIONESE_RE.findall(narrative_text))
    max_action_chain = max(
        (len(STAGE_ACTION_RE.findall(paragraph)) for paragraph in paragraphs),
        default=0,
    )
    adverbial_count = len(ADVERBIAL_RE.findall(text))
    dialogue_ratio = round(dialogue_chars / max(char_count, 1), 3)

    openings = []
    for sentence in narrative_sentences:
        cleaned = sentence.lstrip(" \t“”\"「」『』，,。！？!?；;：:")
        chars = CJK_RE.findall(cleaned[:4])
        if len(chars) >= 2:
            openings.append("".join(chars[:2]))
    opening_counts = Counter(openings)
    top_openings = opening_counts.most_common(6)
    pronoun_start_ratio = round(
        sum(1 for sentence in narrative_sentences if sentence.lstrip("“”\"「」 ").startswith(PRONOUN_START))
        / max(len(narrative_sentences), 1),
        3,
    )
    top_opening_share = round(top_openings[0][1] / max(len(openings), 1), 3) if top_openings else 0.0

    repeated_ngrams = _top_ngrams(narrative_text)

    warnings: list[dict[str, str]] = []
    if generic_hits:
        warnings.append(
            {
                "level": "high" if sum(generic_hits.values()) >= 4 else "medium",
                "code": "generic_atmosphere",
                "message": "空泛气氛或总结句较集中。优先改成可观察的动作、物件或空间变化。",
            }
        )
    if prop_exposition_count or translationese_count:
        warnings.append(
            {
                "level": "high" if prop_exposition_count + translationese_count >= 2 else "medium",
                "code": "prop_exposition",
                "message": "信息由告示牌、屏幕或‘看过去’交代。改成人物直接说，或让动作带出信息。",
            }
        )
    if max_action_chain >= 3:
        warnings.append(
            {
                "level": "medium",
                "code": "action_tag_chain",
                "message": "一段内连续堆了三个以上小动作，像舞台提示。只保留会改变局面的动作。",
            }
        )
    if short_beat_run >= 2:
        warnings.append(
            {
                "level": "high" if short_beat_run >= 3 else "medium",
                "code": "fake_beat_paragraphs",
                "message": "连续用纯叙述单句短段制造停顿。把普通信息并入相邻动作，单句只留给对白或关键变化。",
            }
        )
    if explanation_hits:
        warnings.append(
            {
                "level": "high" if sum(explanation_hits.values()) >= 5 else "medium",
                "code": "over_explanation",
                "message": "解释性连接句偏多。先删‘原来/终于明白/她意识到’，检查前面的动作是否已经足够。",
            }
        )
    if elevation_hits:
        warnings.append(
            {
                "level": "high" if sum(elevation_hits.values()) >= 3 else "medium",
                "code": "ai_elevation",
                "message": "检测到虚假升华、总结式顿悟、三项排比或解释性尾句。保留具体后果，删掉意义宣言。",
            }
        )
    if purple_count >= 2:
        warnings.append(
            {
                "level": "high" if purple_count >= 4 else "medium",
                "code": "purple_prose",
                "message": "美貌或魅力的评价性套语偏多。改成人物会注意到的具体特征和动作。",
            }
        )
    abstract_density = _per_1000(abstract_noun_count, narrative_chars)
    if abstract_noun_count >= 5 and abstract_density >= 10:
        warnings.append(
            {
                "level": "medium",
                "code": "abstract_vocabulary",
                "message": "抽象高级词偏密。把它们还原成场景里的物件、动作或关系变化。",
            }
        )
    dash_density = _per_1000(dash_count, char_count)
    if dash_density >= 10:
        warnings.append(
            {
                "level": "low",
                "code": "dash_overuse",
                "message": "破折号密度偏高。确认它们在做停顿、打断或插话，而不是装饰语气。",
            }
        )
    metaphor_density = _per_1000(metaphor_count, narrative_chars)
    if metaphor_density >= 8:
        warnings.append(
            {
                "level": "high" if metaphor_density >= 14 else "medium",
                "code": "metaphor_density",
                "message": "叙述中的比喻标记偏密。逐句删掉没有提高精确度的比喻，保留与 POV 经验有关的那个。",
            }
        )
    sentence_stats = _sentence_stats(sentences)
    if sentence_stats["long_ratio"] >= 0.3:
        warnings.append(
            {
                "level": "medium",
                "code": "long_sentences",
                "message": "长句比例偏高。把承载单一信息的从句拆开，并让动作句承担节奏。",
            }
        )
    if sentence_stats["count"] >= 20 and sentence_stats["stdev"] < 10:
        warnings.append(
            {
                "level": "medium",
                "code": "uniform_sentences",
                "message": "句长波动偏小，读起来容易整齐。主动加入短句、停顿和一句独立成段的信息。",
            }
        )
    if top_opening_share >= 0.25:
        warnings.append(
            {
                "level": "medium",
                "code": "repeated_openings",
                "message": f"高频段首为‘{top_openings[0][0]}’。改用动作、物件、声音或对话进入句子。",
            }
        )
    if pronoun_start_ratio >= 0.55:
        warnings.append(
            {
                "level": "medium",
                "code": "pronoun_openings",
                "message": "过多句子以她/他/我开头。把部分主语隐去，或让动作和物件先出现。",
            }
        )
    if body_inventory_count >= 4:
        warnings.append(
            {
                "level": "medium",
                "code": "body_inventory",
                "message": "身体反应库存偏多。每场只保留一到两个最符合人物注意力的信号。",
            }
        )
    if repeated_ngrams and repeated_ngrams[0][1] >= 4:
        warnings.append(
            {
                "level": "medium",
                "code": "repeated_phrases",
                "message": f"叙述短语‘{repeated_ngrams[0][0]}’反复出现。检查是否为无意识口癖或场景复制。",
            }
        )
    if char_count >= 800 and dialogue_ratio < 0.03:
        warnings.append(
            {
                "level": "low",
                "code": "low_dialogue",
                "message": "对白占比很低。若场景涉及冲突或关系变化，确认是否应该让人物直接交锋。",
            }
        )

    penalty = 0
    penalty += min(24, sum(generic_hits.values()) * 3)
    penalty += min(18, sum(explanation_hits.values()) * 2)
    penalty += min(12, (prop_exposition_count + translationese_count) * 4)
    penalty += 5 if max_action_chain >= 3 else 0
    penalty += 7 if short_beat_run >= 2 else 0
    penalty += min(18, sum(elevation_hits.values()) * 3)
    penalty += min(20, max(0, metaphor_density - 6) * 2)
    penalty += min(10, purple_count * 2)
    penalty += 6 if abstract_noun_count >= 5 and abstract_density >= 10 else 0
    penalty += 3 if dash_density >= 10 else 0
    penalty += 8 if sentence_stats["long_ratio"] >= 0.3 else 0
    penalty += 7 if sentence_stats["count"] >= 20 and sentence_stats["stdev"] < 10 else 0
    penalty += 8 if top_opening_share >= 0.25 else 0
    penalty += 7 if pronoun_start_ratio >= 0.55 else 0
    penalty += 6 if body_inventory_count >= 4 else 0
    penalty += min(10, max(0, repeated_ngrams[0][1] - 3) * 2) if repeated_ngrams else 0

    score = max(0, min(100, 100 - penalty))
    if score >= 85:
        risk_level = "low"
    elif score >= 70:
        risk_level = "moderate"
    else:
        risk_level = "high"

    return {
        "summary": {
            "char_count": char_count,
            "paragraph_count": len(paragraphs),
            "sentence_count": len(sentences),
            "dialogue_ratio": dialogue_ratio,
            "risk_score": score,
            "risk_level": risk_level,
        },
        "sentence_stats": sentence_stats,
        "paragraph_stats": paragraph_stats,
        "style_markers": {
            "metaphor_count": metaphor_count,
            "metaphor_per_1000_chars": metaphor_density,
            "emotion_label_count": emotion_count,
            "body_inventory_count": body_inventory_count,
            "adverbial_de_count": adverbial_count,
            "adverbial_de_per_1000_chars": _per_1000(adverbial_count, char_count),
            "purple_prose_count": purple_count,
            "abstract_noun_count": abstract_noun_count,
            "dash_per_1000_chars": _per_1000(dash_count, char_count),
            "prop_exposition_count": prop_exposition_count,
            "translationese_count": translationese_count,
            "max_action_chain": max_action_chain,
            "max_short_narrative_run": short_beat_run,
            "pronoun_start_ratio": pronoun_start_ratio,
            "top_sentence_openings": top_openings,
            "top_opening_share": top_opening_share,
            "repeated_ngrams": repeated_ngrams,
        },
        "generic_patterns": generic_hits,
        "explanation_patterns": explanation_hits,
        "ai_elevation_patterns": elevation_hits,
        "warnings": warnings,
    }


def report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
