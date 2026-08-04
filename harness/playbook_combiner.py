"""Playbook combiner: cross-combine atomic play templates to create novel variants.

Given two or more playbook YAML files, uses LLM to produce a fused playbook
that combines the iron rules, escalation axes, and scene templates from each.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel

from .prompt_templates import COMBINE_PLAYS

console = Console()


def combine_two(
    playbook_a: dict,
    playbook_b: dict,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    max_tokens: int = 4096,
) -> Optional[str]:
    """Combine two playbooks into one fused playbook. Returns YAML string."""
    name_a = playbook_a.get("name", "A")
    name_b = playbook_b.get("name", "B")

    console.print(f"融合 [bold]{name_a}[/bold] + [bold]{name_b}[/bold] ...")

    client = OpenAI(api_key=api_key, base_url=base_url)

    prompt = COMBINE_PLAYS.format(
        play_a=name_a,
        play_b=name_b,
        template_a=yaml.dump(playbook_a, allow_unicode=True),
        template_b=yaml.dump(playbook_b, allow_unicode=True),
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.7,
    )

    result = response.choices[0].message.content
    if result:
        console.print(Panel(result[:800], title=f"融合结果: {name_a} × {name_b}"))

    return result


def combine_many(
    playbook_paths: list[str],
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    output_dir: Optional[str] = None,
    pairwise: bool = True,
) -> list[str]:
    """Combine multiple playbooks.

    If pairwise=True, combines every pair. Otherwise, fuses all at once.

    Returns list of saved playbook file paths.
    """
    playbooks = {}
    for path in playbook_paths:
        with open(path) as f:
            data = yaml.safe_load(f)
        playbooks[data.get("name", Path(path).stem)] = data

    names = list(playbooks.keys())
    console.print(f"加载了 [bold]{len(names)}[/bold] 个玩法模板: {', '.join(names)}")

    output_dir = Path(output_dir or "playbooks/combined")
    output_dir.mkdir(parents=True, exist_ok=True)

    saved = []

    if pairwise:
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                combined = combine_two(
                    playbooks[name_a], playbooks[name_b],
                    api_key, base_url, model,
                )
                if combined:
                    filename = output_dir / f"{name_a}_{name_b}.yaml"
                    with open(filename, "w") as f:
                        f.write(combined)
                    saved.append(str(filename))
                    console.print(f"  [green]✓[/green] {filename}")
    else:
        # Fuse all at once (build a mega-template)
        all_yaml = "\n---\n".join(
            yaml.dump(v, allow_unicode=True) for v in playbooks.values()
        )
        client = OpenAI(api_key=api_key, base_url=base_url)
        prompt = (
            f"将以下多种玩法的原子模板融合成一个统一的超级模板：\n\n{all_yaml}"
        )
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.7,
        )
        result = response.choices[0].message.content
        if result:
            filename = output_dir / "fused_all.yaml"
            with open(filename, "w") as f:
                f.write(result)
            saved.append(str(filename))

    console.print(f"\n[green]完成: {len(saved)} 个融合模板已保存到 {output_dir}/[/green]")
    return saved


def suggest_combinations(
    playbook_dir: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    top_k: int = 10,
) -> list[tuple[str, str, str]]:
    """Ask LLM to suggest the most interesting playbook combinations.

    Returns list of (play_a, play_b, reason) tuples.
    """
    from .playbook_extractor import load_all_playbooks

    playbooks = load_all_playbooks(playbook_dir)
    names = list(playbooks.keys())

    if len(names) < 2:
        console.print("[yellow]至少需要2个玩法模板才能建议组合[/yellow]")
        return []

    summary = "\n".join(
        f"- {name}: {playbooks[name].get('iron_rules', ['无'])[0][:80]}..."
        for name in names
    )

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = (
        "你是一位H小说创意策划。以下是当前可用的玩法模板：\n\n"
        f"{summary}\n\n"
        f"请推荐 {top_k} 个最有创意的两两组合方案。对每个组合，说明为什么这两个玩法叠加会产生独特的化学反应。\n\n"
        "输出格式：\n"
        "1. 玩法A + 玩法B：理由（一句话）"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.8,
    )

    result = response.choices[0].message.content or ""

    import re
    suggestions = re.findall(
        r"(\S+)\s*\+\s*(\S+)[：:]\s*(.+)", result
    )
    return [(a.strip(), b.strip(), r.strip()) for a, b, r in suggestions[:top_k]]
