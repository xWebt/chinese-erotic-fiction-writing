"""Chapter generation utilities — pure text processing, no API dependency.

Handles outline parsing, scene segmentation, word counting, and text assembly.
The host Agent performs the actual LLM generation using templates from prompt_templates.py.
"""

import re


def count_chinese(text: str) -> int:
    """Count Chinese characters (excluding punctuation and whitespace)."""
    return len(re.findall(r"[一-鿿]", text))


def count_total(text: str) -> int:
    """Count total characters after stripping markdown formatting."""
    cleaned = re.sub(r"[#\-\*>\s]", "", text)
    return len(cleaned)


def parse_scenes(outline: str, total_words: int) -> list[dict]:
    """Parse scene segments from an LLM-generated chapter outline.

    Returns list of {"brief": str, "words": int} dicts.
    """
    scenes = []

    patterns = [
        r"(?:场景|第)[一二三四五六七八九十\d]+[段部分]?[：:](.*?)(?=(?:场景|第)[一二三四五六七八九十\d]+[段部分]?[：:]|\Z)",
        r"\d+[\.\、\)]\s*(?:场景|段)[：:]?\s*(.+?)(?=\d+[\.\、\)]\s*(?:场景|段)|\Z)",
        r"\d+[\.\、\)]\s*(.+?)(?=\d+[\.\、\)]\s|\Z)",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, outline, re.DOTALL)
        if len(matches) >= 2:
            for m in matches:
                m = m.strip()
                if len(m) > 10:
                    scenes.append({"brief": m[:200]})
            break

    if not scenes:
        scenes = [{"brief": outline[:300]}]

    n = len(scenes)
    for i, s in enumerate(scenes):
        if n == 1:
            s["words"] = total_words
        elif i == 0 or i == n - 1:
            s["words"] = int(total_words / n * 0.8)
        else:
            s["words"] = int(total_words / n * 1.2)

    return scenes


def assemble_chapter(scenes: list[str]) -> dict:
    """Join scene texts into a full chapter. Returns stats dict."""
    full_text = "\n\n".join(scenes)
    return {
        "full_text": full_text,
        "total_chars": count_total(full_text),
        "hanzi": count_chinese(full_text),
        "scene_count": len(scenes),
    }


def check_completion(text: str, target_words: int) -> float:
    """Return completion ratio (0.0-1.0)."""
    actual = count_total(text)
    return min(actual / target_words, 1.0) if target_words > 0 else 1.0
