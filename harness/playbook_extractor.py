"""Playbook extractor: LLM-driven discovery of play patterns from indexed corpus.

Scans the indexed passage database, sends sampled passages to DeepSeek API
for play pattern identification, clusters similar patterns, and outputs
structured YAML playbook files (atomic templates).

Playbooks are stored as YAML files — human-readable, editable, shareable.
They contain only abstract technique patterns, not copyrighted text.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Optional

import yaml
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel

from .prompt_templates import DISCOVER_PLAY_TYPES, EXTRACT_PLAYBOOK

console = Console()


PLAYBOOK_SCHEMA = """## {name}

### 铁律
{iron_rules}

### 升级轴
{escalation_axis}

### 场景模板
{scene_templates}

### 句式库
{sentence_bank}

### 禁忌清单
{taboos}
"""


def _sample_passages(db_path: str, play_type: Optional[str], n: int = 50) -> list[dict]:
    """Sample high-scoring passages from the index."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if play_type:
        rows = conn.execute(
            "SELECT * FROM passages WHERE play_types LIKE ? AND score >= 3 "
            "ORDER BY score DESC LIMIT ?",
            (f"%{play_type}%", n * 2),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM passages WHERE score >= 5 ORDER BY score DESC LIMIT ?",
            (n * 2,),
        ).fetchall()

    conn.close()

    # Diversity sampling: take top N but ensure different source files
    seen_files = set()
    diverse = []
    for row in rows:
        if row["file_path"] not in seen_files:
            seen_files.add(row["file_path"])
            diverse.append(dict(row))
        if len(diverse) >= n:
            break

    return diverse


def _estimate_cost(model: str, prompt_tokens: int, completion_tokens: int = 2000) -> float:
    """Estimate DeepSeek API cost in USD."""
    # DeepSeek pricing (approx): ~$0.14/1M input, ~$0.28/1M output
    input_cost = prompt_tokens / 1_000_000 * 0.14
    output_cost = completion_tokens / 1_000_000 * 0.28
    return round(input_cost + output_cost, 4)


def discover_play_types(
    db_path: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    max_passages: int = 60,
    max_tokens: int = 4096,
) -> list[str]:
    """Ask LLM to discover play types from a sample of the indexed corpus.

    Returns a list of discovered play type names.
    """
    passages = _sample_passages(db_path, play_type=None, n=max_passages)
    if not passages:
        console.print("[red]索引中没有足够的段落。请先运行索引。[/red]")
        return []

    # Build prompt with sampled passages
    texts = [p["text"][:600] for p in passages[:max_passages]]
    combined = "\n\n---\n\n".join(
        f"[段落 {i + 1}]\n{t}" for i, t in enumerate(texts)
    )

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = DISCOVER_PLAY_TYPES.format(passages=combined[:8000])

    est_cost = _estimate_cost(model, len(prompt) // 2 + len(combined[:8000]) // 2, max_tokens)
    console.print(f"发现玩法类型中... (预估成本: ${est_cost})")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )

    result = response.choices[0].message.content
    console.print(Panel(result or "(无输出)", title="LLM 发现的玩法类型"))

    # Parse play type names from the result
    # LLM output format: "1. **露出** - ..." or similar
    import re
    names = re.findall(r"(?:\d+\.\s*\*{0,2})([^\s\*\-：:]+)", result or "")
    if not names:
        names = re.findall(r"玩法名称[：:]\s*(.+)", result or "")
    if not names:
        # Fallback: try to find bold text
        names = re.findall(r"\*\*([^*]{2,8})\*\*", result or "")

    # Deduplicate while preserving order
    seen = set()
    unique_names = []
    for n in names:
        n = n.strip()
        if n and n not in seen and len(n) <= 10:
            seen.add(n)
            unique_names.append(n)

    return unique_names[:20]


def extract_playbook(
    db_path: str,
    play_type: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    max_passages: int = 40,
    max_tokens: int = 4096,
) -> Optional[str]:
    """Extract a single playbook for a specific play type.

    Returns the playbook YAML string, or None on failure.
    """
    passages = _sample_passages(db_path, play_type=play_type, n=max_passages)
    if len(passages) < 5:
        console.print(f"[yellow]玩法 [{play_type}] 的段落不足 ({len(passages)} 段)，跳过[/yellow]")
        return None

    texts = [p["text"][:500] for p in passages[:max_passages]]
    combined = "\n\n---\n\n".join(
        f"[段落 {i + 1}]\n{t}" for i, t in enumerate(texts)
    )

    client = OpenAI(api_key=api_key, base_url=base_url)
    prompt = EXTRACT_PLAYBOOK.format(play_type=play_type, passages=combined[:8000])

    console.print(f"提取 [{play_type}] 玩法模板中...")

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.3,
    )

    result = response.choices[0].message.content
    if not result:
        console.print(f"[red][{play_type}] LLM 未返回结果[/red]")
        return None

    # Parse into structured YAML
    yaml_data = _parse_playbook_to_yaml(play_type, result)
    return yaml_data


def _parse_playbook_to_yaml(play_type: str, llm_output: str) -> str:
    """Convert LLM markdown output to structured YAML."""
    import re

    data = {"name": play_type}

    # Extract sections
    sections = {
        "铁律": "iron_rules",
        "升级轴": "escalation_axis",
        "场景模板": "scene_templates",
        "句式库": "sentence_bank",
        "禁忌清单": "taboos",
    }

    for cn, en in sections.items():
        # Match "## 铁律" or "### 铁律" style headers
        pattern = rf"#{{1,3}}\s*{cn}\s*\n(.*?)(?=\n#{{1,3}}\s|\Z)"
        match = re.search(pattern, llm_output, re.DOTALL)
        if match:
            content = match.group(1).strip()
            # Split numbered list items
            items = re.findall(r"(?:^\d+[\.\、\)]\s*|^[-*]\s+)(.+)", content, re.MULTILINE)
            if items:
                data[en] = [i.strip() for i in items]
            else:
                data[en] = content

    return yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)


def extract_all_playbooks(
    db_path: str,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    model: str = "deepseek-chat",
    output_dir: Optional[str] = None,
    play_types: Optional[list[str]] = None,
) -> list[str]:
    """Full pipeline: discover play types, then extract playbook for each.

    Args:
        db_path: Path to SQLite index DB.
        api_key: DeepSeek API key.
        base_url: DeepSeek API base URL.
        model: Model name.
        output_dir: Where to save YAML playbook files.
        play_types: Pre-defined play types (skips discovery if provided).

    Returns:
        List of saved playbook file paths.
    """
    if play_types is None:
        play_types = discover_play_types(db_path, api_key, base_url, model)

    if not play_types:
        console.print("[red]未发现任何玩法类型[/red]")
        return []

    console.print(f"\n将提取 [bold]{len(play_types)}[/bold] 种玩法的原子模板: {', '.join(play_types)}")

    output_dir = Path(output_dir or "playbooks")
    output_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for pt in play_types:
        yaml_content = extract_playbook(db_path, pt, api_key, base_url, model)
        if yaml_content:
            filename = output_dir / f"{pt}.yaml"
            with open(filename, "w") as f:
                f.write(yaml_content)
            saved.append(str(filename))
            console.print(f"  [green]✓[/green] {filename}")

    console.print(f"\n[green]完成: {len(saved)}/{len(play_types)} 个玩法模板已保存到 {output_dir}/[/green]")
    return saved


def load_playbook(playbook_path: str) -> dict:
    """Load a YAML playbook into a dict."""
    with open(playbook_path) as f:
        return yaml.safe_load(f)


def load_all_playbooks(playbooks_dir: str) -> dict[str, dict]:
    """Load all YAML playbooks from a directory. Returns {name: data}."""
    playbooks = {}
    for f in Path(playbooks_dir).glob("*.yaml"):
        data = load_playbook(str(f))
        name = data.get("name", f.stem)
        playbooks[name] = data
    return playbooks
