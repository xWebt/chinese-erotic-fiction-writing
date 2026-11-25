"""Select diverse, bounded scenes from a long Chinese text for style review."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from .corpus_style import DIALOGUE_RE, profile_text
from .text_encoding import read_text_prefix

ACTION_RE = re.compile(
    r"走|跑|推|拉|拿|放|坐|站|转|抬|低|看|问|说|笑|停|敲|开|关|递|接|抓|按|挡|退"
)
EXPLICIT_RE = re.compile(
    r"吻|亲|抱|摸|揉|脱|裸|胸|乳|腿|腰|喘|呻吟|湿|热|颤|穴|阴茎|阴蒂|高潮"
)
CHAPTER_RE = re.compile(
    r"(?m)^(?:第[一二三四五六七八九十百千万零〇\d]+[章节回折卷幕部篇].*|"
    r"(?:序章|楔子|前言|后记).*)$"
)


@dataclass
class Scene:
    category: str
    text: str
    score: float
    position: float


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(?i)(?:www\.|https?://)\S+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _paragraph_windows(text: str, target_chars: int = 1200) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n+", text) if part.strip()]
    windows: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        length = len(paragraph)
        if current and current_len + length > target_chars * 1.35:
            windows.append("\n\n".join(current))
            current = current[-1:]
            current_len = len(current[0]) if current else 0
        current.append(paragraph)
        current_len += length
        if current_len >= target_chars:
            windows.append("\n\n".join(current))
            current = []
            current_len = 0
    if current:
        windows.append("\n\n".join(current))
    return windows


def _scene_score(text: str, kind: str) -> float:
    profile = profile_text(text)
    cjk = max(1, profile.get("cjk_chars", 0))
    dialogue = DIALOGUE_RE.findall(text)
    dialogue_ratio = sum(len(item) for item in dialogue) / cjk
    action_density = len(ACTION_RE.findall(text)) * 1000 / cjk
    explicit_density = len(EXPLICIT_RE.findall(text)) * 1000 / cjk
    if kind == "dialogue":
        return dialogue_ratio * 10 + action_density / 10
    if kind == "action":
        return action_density + dialogue_ratio * 2
    if kind == "intimate":
        return explicit_density * 2 + dialogue_ratio
    if kind == "narrative":
        return (1 - min(dialogue_ratio, 1)) * 3 + action_density / 15
    return 1 - abs(dialogue_ratio - 0.18) + action_density / 20


def select_scenes(text: str, count: int = 6, target_chars: int = 1200) -> list[Scene]:
    text = _normalize(text)
    # Keep the first major chunk so openings are represented, then move gradually.
    windows = _paragraph_windows(text, target_chars=target_chars)
    if not windows:
        return []

    categories = ["narrative", "dialogue", "action", "intimate", "narrative", "dialogue"]
    selected: list[Scene] = []
    used: set[int] = set()
    for index, category in enumerate(categories[:count]):
        lower = int(index * len(windows) / count)
        upper = int((index + 1) * len(windows) / count)
        candidates = range(lower, max(lower + 1, upper))
        scored = [
            Scene(category, windows[i], _scene_score(windows[i], category), i / len(windows))
            for i in candidates
            if i not in used and len(windows[i]) >= max(300, target_chars // 3)
        ]
        if not scored:
            continue
        choice = max(scored, key=lambda scene: scene.score)
        used.add(int(choice.position * len(windows)))
        selected.append(choice)
    return selected


def sample_file(path: str | Path, count: int = 6, target_chars: int = 1200) -> list[Scene]:
    text, _encoding, _score = read_text_prefix(path, byte_limit=350_000)
    return select_scenes(text, count=count, target_chars=target_chars)


def render_scenes(scenes: Iterable[Scene]) -> str:
    blocks = []
    for index, scene in enumerate(scenes, 1):
        blocks.append(
            f"[SCENE {index} | {scene.category} | position={scene.position:.2f}]\n"
            f"{scene.text}"
        )
    return "\n\n".join(blocks)
