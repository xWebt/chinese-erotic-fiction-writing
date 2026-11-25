"""Compact corpus style profiler.

Reads only a bounded prefix of each file and emits aggregate prose metrics.
It avoids putting full corpus text into the agent context.
"""

from __future__ import annotations

from pathlib import Path
import json
import re
import statistics
from typing import Any, Iterable

from .text_encoding import read_text_prefix

CJK_RE = re.compile(r"[\u3400-\u9fff]")
SENTENCE_RE = re.compile(r"(?<=[。！？!?])\s*")
DIALOGUE_RE = re.compile(r"“[^”]*”|「[^」]*」|『[^』]*』|\"[^\"\\n]*\"")
METAPHOR_RE = re.compile(r"仿佛|像是|如同|宛如|好似|犹如|恍若|像(?!片|素|样|册|机)")
def _cjk_len(text: str) -> int:
    return len(CJK_RE.findall(text))




def _read_prefix(path: Path, byte_limit: int = 120_000) -> str:
    text, _encoding, _score = read_text_prefix(path, byte_limit=byte_limit)
    return text.replace("\r", "\n")


def profile_text(text: str) -> dict[str, Any]:
    """Return aggregate style metrics for a text sample."""
    text = text.strip()
    cjk_chars = _cjk_len(text)
    if not cjk_chars:
        return {"cjk_chars": 0}

    dialogue_text = "".join(DIALOGUE_RE.findall(text))
    narrative = DIALOGUE_RE.sub("", text)
    sentences = [s.strip() for s in SENTENCE_RE.split(text) if _cjk_len(s)]
    sentence_lengths = [_cjk_len(s) for s in sentences]
    paragraphs = [p.strip() for p in re.split(r"\n+", text) if _cjk_len(p) >= 2]
    paragraph_lengths = [_cjk_len(p) for p in paragraphs]
    one_sentence = 0
    for paragraph in paragraphs:
        parts = [part for part in SENTENCE_RE.split(paragraph) if _cjk_len(part)]
        if len(parts) == 1:
            one_sentence += 1

    return {
        "cjk_chars": cjk_chars,
        "sentences": len(sentence_lengths),
        "median_sentence": round(statistics.median(sentence_lengths), 1)
        if sentence_lengths
        else 0,
        "mean_sentence": round(statistics.mean(sentence_lengths), 1)
        if sentence_lengths
        else 0,
        "dialogue_ratio": round(_cjk_len(dialogue_text) / cjk_chars, 3),
        "median_paragraph": round(statistics.median(paragraph_lengths), 1)
        if paragraph_lengths
        else 0,
        "one_sentence_paragraph_ratio": round(
            one_sentence / max(len(paragraphs), 1), 3
        ),
        "metaphor_per_1000": round(
            len(METAPHOR_RE.findall(narrative)) * 1000 / cjk_chars, 2
        ),
    }


def _expand_paths(paths: Iterable[str], limit: int) -> list[Path]:
    files: list[Path] = []
    for value in paths:
        path = Path(value)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.txt")))
        elif path.is_file():
            files.append(path)
    if len(files) > limit:
        step = (len(files) - 1) / max(limit - 1, 1)
        files = [files[round(i * step)] for i in range(limit)]
    return files


def profile_paths(paths: Iterable[str], limit: int = 30) -> dict[str, Any]:
    files = _expand_paths(paths, limit)
    profiles: list[dict[str, Any]] = []
    for path in files:
        try:
            profile = profile_text(_read_prefix(path))
        except OSError:
            continue
        if profile.get("cjk_chars", 0) >= 1500:
            profile["file"] = str(path)
            profiles.append(profile)

    if not profiles:
        return {"sample_count": 0}

    keys = [
        "median_sentence",
        "mean_sentence",
        "dialogue_ratio",
        "median_paragraph",
        "one_sentence_paragraph_ratio",
        "metaphor_per_1000",
    ]
    summary: dict[str, Any] = {
        "sample_count": len(profiles),
        "files_scanned": len(files),
    }
    for key in keys:
        values = sorted(float(profile[key]) for profile in profiles)
        summary[key] = {
            "p25": round(values[len(values) // 4], 2),
            "median": round(statistics.median(values), 2),
            "p75": round(values[min(len(values) - 1, len(values) * 3 // 4)], 2),
        }
    summary["samples"] = profiles
    return summary


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
