"""Playbook extractor — pure prompt generation, no API dependency.

Generates structured prompts for the host Agent to use when discovering
play patterns from indexed corpus passages. The Agent reads these prompts
and calls its own LLM backend.
"""

import yaml
from pathlib import Path
from typing import Optional

from .prompt_templates import DISCOVER_PLAY_TYPES, EXTRACT_PLAYBOOK


def build_discovery_prompt(passages: list[str]) -> str:
    """Build a prompt for the Agent to discover play types from sampled passages.

    Args:
        passages: List of passage texts (already sampled and filtered).

    Returns:
        Formatted prompt string ready for the Agent's LLM.
    """
    combined = "\n\n---\n\n".join(
        f"[段落 {i + 1}]\n{t}" for i, t in enumerate(passages)
    )
    return DISCOVER_PLAY_TYPES.format(passages=combined[:8000])


def build_extraction_prompt(play_type: str, passages: list[str]) -> str:
    """Build a prompt for extracting an atomic playbook for a specific play type.

    Args:
        play_type: The play type name (e.g. "露出", "调教").
        passages: Relevant passage texts.

    Returns:
        Formatted prompt string ready for the Agent's LLM.
    """
    combined = "\n\n---\n\n".join(
        f"[段落 {i + 1}]\n{t[:500]}" for i, t in enumerate(passages)
    )
    return EXTRACT_PLAYBOOK.format(play_type=play_type, passages=combined[:8000])


def parse_playbook_to_yaml(play_type: str, llm_output: str) -> str:
    """Convert LLM markdown output to structured YAML.

    Extracts 铁律, 升级轴, 场景模板, 句式库, 禁忌清单 sections.
    """
    import re

    data = {"name": play_type}
    sections = {
        "铁律": "iron_rules",
        "升级轴": "escalation_axis",
        "场景模板": "scene_templates",
        "句式库": "sentence_bank",
        "禁忌清单": "taboos",
    }

    for cn, en in sections.items():
        pattern = rf"#{{1,3}}\s*{cn}\s*\n(.*?)(?=\n#{{1,3}}\s|\Z)"
        match = re.search(pattern, llm_output, re.DOTALL)
        if match:
            content = match.group(1).strip()
            items = re.findall(r"(?:^\d+[\.\、\)]\s*|^[-*]\s+)(.+)", content, re.MULTILINE)
            if items:
                data[en] = [i.strip() for i in items]
            else:
                data[en] = content

    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def load_playbook(playbook_path: str) -> dict:
    """Load a YAML playbook into a dict."""
    with open(playbook_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_playbooks(playbooks_dir: str) -> dict[str, dict]:
    """Load all YAML playbooks from a directory. Returns {name: data}."""
    playbooks = {}
    for f in Path(playbooks_dir).glob("*.yaml"):
        data = load_playbook(str(f))
        name = data.get("name", f.stem)
        playbooks[name] = data
    return playbooks
