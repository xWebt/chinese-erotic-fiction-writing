"""Chinese text decoding helpers with plausibility-based encoding selection."""

from __future__ import annotations

from pathlib import Path

CJK_MIN = 0x3400
CJK_MAX = 0x9FFF
COMMON_PUNCT = set("，。！？：；、“”‘’（）《》【】…—\n\t ")
COMMON_CHARS = set("的了是在不我他她这那有和就人说中上下来去着到为子你")
CANDIDATE_ENCODINGS = ("utf-8-sig", "gb18030", "big5")


def _is_cjk(char: str) -> bool:
    return CJK_MIN <= ord(char) <= CJK_MAX


def decode_quality(text: str) -> float:
    """Heuristic quality score for a candidate Chinese decoding."""
    if not text:
        return float("-inf")
    cjk = sum(_is_cjk(char) for char in text)
    punctuation = sum(char in COMMON_PUNCT for char in text)
    common = sum(char in COMMON_CHARS for char in text)
    replacement = text.count("\ufffd")
    controls = sum(ord(char) < 32 and char not in "\n\r\t" for char in text)
    pua = sum(0xE000 <= ord(char) <= 0xF8FF for char in text)
    return cjk + punctuation * 2 + common * 0.25 - replacement * 80 - controls * 20 - pua * 30


def decode_bytes(raw: bytes) -> tuple[str, str, float]:
    """Decode bytes using the most plausible Chinese encoding."""
    candidates: list[tuple[float, str, str]] = []
    for encoding in CANDIDATE_ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            text = raw.decode(encoding, errors="replace")
        candidates.append((decode_quality(text[:120_000]), encoding, text))

    if candidates:
        score, encoding, text = max(candidates, key=lambda item: item[0])
        return text, encoding, score

    text = raw.decode("utf-8", errors="replace")
    return text, "utf-8-fallback", decode_quality(text)


def read_text_prefix(path: str | Path, byte_limit: int = 120_000) -> tuple[str, str, float]:
    raw = Path(path).read_bytes()[:byte_limit]
    return decode_bytes(raw)
