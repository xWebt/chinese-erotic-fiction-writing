"""Audit Codex session token usage without loading prompts or outputs."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any


def audit_session(path: str | Path, budget: int = 1_000_000) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("type") == "token_usage_record":
                records.append(item.get("payload", {}))

    if not records:
        return {"session": str(path), "error": "no token_usage_record"}

    latest = records[-1].get("thread_token_usage", {})
    total = int(latest.get("total_tokens", 0))
    input_tokens = int(latest.get("input_tokens", 0))
    cached = int(latest.get("cached_input_tokens", 0))
    output = int(latest.get("output_tokens", 0))
    reasoning = int(latest.get("reasoning_output_tokens", 0))
    context_overhead = input_tokens + cached

    turns: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for record in records:
        turn_id = record.get("turn_id", "unknown")
        for key, value in record.get("usage", {}).items():
            turns[turn_id][key] += int(value or 0)

    warnings: list[str] = []
    if total > budget:
        warnings.append(f"thread usage exceeds budget: {total} > {budget}")
    if total and context_overhead / total >= 0.95:
        warnings.append("over 95% of processed tokens are input/context")
    if total and output / total < 0.01:
        warnings.append("visible output is below 1% of processed tokens")

    return {
        "session": str(path),
        "responses": len(records),
        "thread": {
            "input_tokens": input_tokens,
            "cached_input_tokens": cached,
            "output_tokens": output,
            "reasoning_output_tokens": reasoning,
            "total_tokens": total,
        },
        "overhead_ratio": round(context_overhead / max(total, 1), 4),
        "output_ratio": round(output / max(total, 1), 4),
        "budget": budget,
        "turns": dict(turns),
        "warnings": warnings,
    }


def to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2)
