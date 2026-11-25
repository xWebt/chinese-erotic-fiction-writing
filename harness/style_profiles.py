"""Load and validate style profiles and playbooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STYLE_DIR = ROOT / "styles"
PLAYBOOK_DIR = ROOT / "playbooks"


def _yaml():
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load skill profiles") from exc
    return yaml


def load_yaml(path: Path) -> dict[str, Any]:
    return _yaml().safe_load(path.read_text(encoding="utf-8")) or {}


def load_style(profile_id: str) -> dict[str, Any]:
    path = STYLE_DIR / f"{profile_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown style profile: {profile_id}")
    profile = load_yaml(path)
    required = ("id", "role", "source", "voice", "sentence", "paragraph", "dialogue", "scene")
    missing = [key for key in required if key not in profile]
    if missing:
        raise ValueError(f"{path.name} missing fields: {', '.join(missing)}")
    return profile


def load_playbook(play_id: str) -> dict[str, Any]:
    path = PLAYBOOK_DIR / f"{play_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Unknown playbook: {play_id}")
    playbook = load_yaml(path)
    required = ("id", "label", "core_tension", "progression", "turn", "avoid")
    missing = [key for key in required if key not in playbook]
    if missing:
        raise ValueError(f"{path.name} missing fields: {', '.join(missing)}")
    return playbook


def list_styles() -> list[str]:
    return sorted(path.stem for path in STYLE_DIR.glob("*.yaml") if not path.name.startswith("_") and path.name != "index")


def list_playbooks() -> list[str]:
    return sorted(path.stem for path in PLAYBOOK_DIR.glob("*.yaml") if path.name != "index")


def context_paths(style_id: str = "plain-modern", module_id: str | None = None, play_id: str | None = None) -> list[str]:
    paths = ["SKILL.md", "core/prose-rules.md", f"styles/{style_id}.yaml"]
    if module_id:
        paths.append(f"styles/{module_id}.yaml")
    if play_id:
        paths.append(f"playbooks/{play_id}.yaml")
    return paths


def evaluate_profile(report: dict[str, Any], profile: dict[str, Any]) -> list[dict[str, str]]:
    """Compare an audit report with a style profile threshold set."""
    thresholds = profile.get("thresholds", {})
    if not thresholds:
        return []
    findings: list[dict[str, str]] = []
    summary = report["summary"]
    sentence = report["sentence_stats"]
    markers = report["style_markers"]

    sentence_range = thresholds.get("sentence_median")
    if sentence_range and not (sentence_range[0] <= sentence["median"] <= sentence_range[1]):
        findings.append({
            "level": "medium",
            "code": "profile_sentence_median",
            "message": f"句子中位 {sentence['median']}，profile 目标 {sentence_range[0]} 至 {sentence_range[1]}。",
        })

    dialogue_range = thresholds.get("dialogue_ratio")
    if dialogue_range and not (dialogue_range[0] <= summary["dialogue_ratio"] <= dialogue_range[1]):
        findings.append({
            "level": "low",
            "code": "profile_dialogue_ratio",
            "message": f"对白占比 {summary['dialogue_ratio']:.1%}，profile 范围 {dialogue_range[0]:.0%} 至 {dialogue_range[1]:.0%}。",
        })

    checks = (
        ("max_short_narrative_run", "max_short_narrative_run", "连续纯叙述短段"),
        ("max_action_chain", "max_action_chain", "单段动作标签"),
        ("metaphor_per_1000_max", "metaphor_per_1000_chars", "比喻密度"),
        ("prop_exposition_max", "prop_exposition_count", "告示牌式交代"),
    )
    for threshold_key, marker_key, label in checks:
        limit = thresholds.get(threshold_key)
        value = markers.get(marker_key)
        if limit is None or value is None or value <= limit:
            continue
        findings.append({
            "level": "high" if threshold_key == "prop_exposition_max" else "medium",
            "code": f"profile_{threshold_key}",
            "message": f"{label} {value}，profile 上限 {limit}。",
        })
    return findings
