"""Playbook combiner — pure prompt generation, no API dependency.

Builds prompts for the host Agent to cross-combine atomic play templates.
"""

import yaml
from pathlib import Path
from typing import Optional

from .prompt_templates import COMBINE_PLAYS


def build_combine_prompt(playbook_a: dict, playbook_b: dict) -> str:
    """Build a prompt for fusing two playbooks into a novel combined variant.

    Args:
        playbook_a: First playbook dict (with name, iron_rules, etc.).
        playbook_b: Second playbook dict.

    Returns:
        Formatted prompt string ready for the Agent's LLM.
    """
    name_a = playbook_a.get("name", "A")
    name_b = playbook_b.get("name", "B")
    return COMBINE_PLAYS.format(
        play_a=name_a,
        play_b=name_b,
        template_a=yaml.dump(playbook_a, allow_unicode=True),
        template_b=yaml.dump(playbook_b, allow_unicode=True),
    )


def build_fusion_prompt(playbooks: dict[str, dict]) -> str:
    """Build a prompt for fusing 3+ playbooks at once."""
    all_yaml = "\n---\n".join(
        yaml.dump(v, allow_unicode=True) for v in playbooks.values()
    )
    return f"将以下多种玩法的原子模板融合成一个统一的超级模板：\n\n{all_yaml}"


def build_suggestion_prompt(playbook_summaries: list[str], top_k: int = 10) -> str:
    """Build a prompt asking the LLM to suggest interesting playbook combinations."""
    summary = "\n".join(playbook_summaries)
    return (
        "你是一位H小说创意策划。以下是当前可用的玩法模板：\n\n"
        f"{summary}\n\n"
        f"请推荐 {top_k} 个最有创意的两两组合方案。对每个组合，说明为什么这两个玩法叠加会产生独特的化学反应。\n\n"
        "输出格式：\n"
        "1. 玩法A + 玩法B：理由（一句话）"
    )


def get_playbook_summaries(playbooks_dir: str) -> list[str]:
    """Get one-line summaries of all playbooks in a directory."""
    summaries = []
    for f in Path(playbooks_dir).glob("*.yaml"):
        with open(f) as fp:
            data = yaml.safe_load(fp)
        name = data.get("name", f.stem)
        rules = data.get("iron_rules", [])
        if isinstance(rules, list) and rules:
            summaries.append(f"- {name}: {rules[0][:80]}...")
        elif isinstance(rules, str):
            summaries.append(f"- {name}: {rules[:80]}...")
        else:
            summaries.append(f"- {name}")
    return summaries
