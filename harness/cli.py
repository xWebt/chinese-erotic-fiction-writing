"""CLI entry point for the Chinese fiction writing harness.

Commands:
    novel init        Initialize configuration
    novel index       Build corpus index from .txt files
    novel calibrate   Compute anchor baseline
    novel extract     Extract playbook templates via LLM
    novel combine     Combine playbooks into new variants
    novel generate    Generate a chapter
    novel wordcount   Count words in a file
"""

import json
import os
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import Config

console = Console()


@click.group()
@click.option("--config", "-c", "config_path", default=None, help="Config file path")
@click.pass_context
def main(ctx, config_path):
    """Chinese Fiction Harness — AI-assisted novel writing with DeepSeek."""
    ctx.ensure_object(dict)
    cfg = Config.load(Path(config_path) if config_path else None)
    ctx.obj["cfg"] = cfg


# ── init ──────────────────────────────────────────────

@main.command()
@click.option("--api-key", prompt=True, hide_input=True, help="DeepSeek API key")
@click.option("--corpus-dir", prompt=True, help="Path to corpus directory")
@click.option("--anchor", "-a", multiple=True, help="Anchor work file names")
@click.pass_context
def init(ctx, api_key, corpus_dir, anchor):
    """Initialize configuration."""
    cfg: Config = ctx.obj["cfg"]
    cfg.deepseek_api_key = api_key
    cfg.corpus_dir = corpus_dir
    cfg.anchor_works = list(anchor)
    cfg.save()
    console.print(f"[green]配置已保存到 {Config.CONFIG_FILE}[/green]")
    console.print(f"  语料目录: {cfg.corpus_dir}")
    console.print(f"  索引目录: {cfg.index_dir}")
    console.print(f"  指纹目录: {cfg.fingerprints_dir}")


# ── index ─────────────────────────────────────────────

@main.command()
@click.option("--corpus-dir", "-d", default=None, help="Corpus directory (uses config if omitted)")
@click.option("--db", default=None, help="Output SQLite DB path")
@click.option("--anchor", "-a", multiple=True, help="Anchor file names")
@click.option("--min-score", default=2, help="Minimum technique score to keep (default: 2)")
@click.pass_context
def index(ctx, corpus_dir, db, anchor, min_score):
    """Build corpus index from text files."""
    from .corpus_indexer import build_index

    cfg: Config = ctx.obj["cfg"]
    corpus_dir = corpus_dir or cfg.corpus_dir
    db_path = db or os.path.join(cfg.index_dir, "corpus.db")
    anchors = list(anchor) if anchor else cfg.anchor_works

    if not corpus_dir:
        console.print("[red]请指定语料目录 (--corpus-dir 或运行 novel init)[/red]")
        return

    build_index(corpus_dir, db_path, anchors, min_score=min_score)


# ── calibrate ─────────────────────────────────────────

@main.command()
@click.option("--db", default=None, help="Index DB path")
@click.option("--anchor", "-a", multiple=True, help="Anchor file name patterns")
@click.option("--strictness", "-s", type=float, default=0.5, help="Threshold strictness 0-1 (default 0.5)")
@click.option("--output", "-o", default=None, help="Save baseline to JSON file")
@click.pass_context
def calibrate(ctx, db, anchor, strictness, output):
    """Compute technique baseline from anchor works."""
    from .anchor_calibrator import calibrate as do_calibrate, set_thresholds

    cfg: Config = ctx.obj["cfg"]
    db_path = db or os.path.join(cfg.index_dir, "corpus.db")
    anchors = list(anchor) if anchor else cfg.anchor_works

    if not anchors:
        console.print("[red]请指定锚点作品 (--anchor 或配置中设置 anchor_works)[/red]")
        return

    baseline = do_calibrate(db_path, anchors)
    if not baseline:
        return

    thresholds = set_thresholds(baseline, strictness)
    console.print(f"\n阈值 (strictness={strictness}):")
    for k, v in thresholds.items():
        console.print(f"  {k}: {v}")

    if output:
        result = {"baseline": baseline, "thresholds": thresholds}
        with open(output, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        console.print(f"[green]基线已保存到 {output}[/green]")


# ── extract ───────────────────────────────────────────

@main.command()
@click.option("--db", default=None, help="Index DB path")
@click.option("--output-dir", "-o", default=None, help="Playbook output directory")
@click.option("--play-type", "-p", "play_types", multiple=True, help="Play type to extract (repeatable; skip discovery)")
@click.option("--api-key", default=None, help="DeepSeek API key (uses config if omitted)")
@click.option("--base-url", default="https://api.deepseek.com")
@click.option("--model", default="deepseek-chat")
@click.pass_context
def extract(ctx, db, output_dir, play_types, api_key, base_url, model):
    """Extract atomic playbook templates via LLM."""
    from .playbook_extractor import extract_all_playbooks

    cfg: Config = ctx.obj["cfg"]
    db_path = db or os.path.join(cfg.index_dir, "corpus.db")
    api_key = api_key or cfg.deepseek_api_key
    output_dir = output_dir or cfg.fingerprints_dir

    if not api_key:
        console.print("[red]请提供 DeepSeek API key (--api-key 或配置中设置)[/red]")
        return

    if not os.path.exists(db_path):
        console.print(f"[red]索引数据库不存在: {db_path}。请先运行 novel index[/red]")
        return

    pt_list = list(play_types) if play_types else None
    extract_all_playbooks(db_path, api_key, base_url, model, output_dir, pt_list)


# ── combine ───────────────────────────────────────────

@main.command()
@click.option("--playbooks-dir", "-d", default=None, help="Directory containing playbook YAML files")
@click.option("--output-dir", "-o", default=None, help="Output directory for combined playbooks")
@click.option("--api-key", default=None)
@click.option("--base-url", default="https://api.deepseek.com")
@click.option("--model", default="deepseek-chat")
@click.option("--suggest", is_flag=True, help="Ask LLM to suggest interesting combinations first")
@click.pass_context
def combine(ctx, playbooks_dir, output_dir, api_key, base_url, model, suggest):
    """Combine playbooks to create new play variants."""
    from .playbook_combiner import combine_many, suggest_combinations

    cfg: Config = ctx.obj["cfg"]
    api_key = api_key or cfg.deepseek_api_key
    playbooks_dir = playbooks_dir or cfg.fingerprints_dir

    if not playbooks_dir or not Path(playbooks_dir).exists():
        console.print(f"[red]玩法模板目录不存在: {playbooks_dir}[/red]")
        return

    if suggest:
        suggestions = suggest_combinations(playbooks_dir, api_key, base_url, model)
        console.print("\n[bold]建议的组合:[/bold]")
        for a, b, reason in suggestions:
            console.print(f"  [cyan]{a}[/cyan] + [cyan]{b}[/cyan]: {reason}")

    files = list(Path(playbooks_dir).glob("*.yaml"))
    if len(files) < 2:
        console.print("[red]至少需要2个玩法模板文件才能组合[/red]")
        return

    combine_many([str(f) for f in files], api_key, base_url, model, output_dir)


# ── generate ──────────────────────────────────────────

@main.command()
@click.option("--play-types", "-p", required=True, help="Comma-separated play types, e.g. '露出,古风'")
@click.option("--setting", "-s", required=True, help="Scene setting, e.g. '御花园假山后'")
@click.option("--perspective", default="第三人称", help="Narrative perspective")
@click.option("--target-words", "-w", type=int, default=5000, help="Target word count (default: 5000)")
@click.option("--characters", "-c", default="", help="Character descriptions")
@click.option("--previous", default="", help="Previous chapter context (file or text)")
@click.option("--playbooks-dir", default=None, help="Playbook YAML directory")
@click.option("--db", default=None, help="Index DB for style references")
@click.option("--api-key", default=None)
@click.option("--base-url", default="https://api.deepseek.com")
@click.option("--model", default="deepseek-chat")
@click.option("--max-continue", type=int, default=4, help="Max auto-continue rounds (default: 4)")
@click.option("--output", "-o", default=None, help="Save chapter to file")
@click.pass_context
def generate(
    ctx, play_types, setting, perspective, target_words, characters,
    previous, playbooks_dir, db, api_key, base_url, model, max_continue, output,
):
    """Generate a chapter using DeepSeek API."""
    from .chapter_generator import ChapterGenerator

    cfg: Config = ctx.obj["cfg"]
    api_key = api_key or cfg.deepseek_api_key
    playbooks_dir = playbooks_dir or cfg.fingerprints_dir
    db_path = db or os.path.join(cfg.index_dir, "corpus.db")

    if not api_key:
        console.print("[red]请提供 DeepSeek API key[/red]")
        return

    # Load previous context from file if it's a path
    if previous and os.path.exists(previous):
        with open(previous) as f:
            previous = f.read()[-2000:]  # Last 2000 chars as context

    play_list = [p.strip() for p in play_types.split(",")]

    gen = ChapterGenerator(
        api_key=api_key,
        base_url=base_url,
        model=model,
        db_path=db_path if os.path.exists(db_path) else None,
    )

    result = gen.generate_chapter(
        play_types=play_list,
        setting=setting,
        perspective=perspective,
        target_words=target_words,
        characters=characters,
        previous_context=previous,
        playbooks_dir=playbooks_dir if os.path.exists(playbooks_dir) else None,
        max_continue_rounds=max_continue,
    )

    if "error" in result:
        console.print(f"[red]{result['error']}[/red]")
        return

    if output:
        with open(output, "w") as f:
            f.write(result["full_text"])
        console.print(f"[green]章节已保存到 {output}[/green]")
    else:
        console.print("\n" + "=" * 60)
        console.print(result["full_text"])
        console.print("=" * 60)


# ── wordcount ─────────────────────────────────────────

@main.command()
@click.argument("filepath")
@click.option("--threshold", "-t", type=int, default=5000, help="Pass threshold (default: 5000)")
def wordcount(filepath, threshold):
    """Count words per chapter in a markdown novel file."""
    import re

    if not os.path.exists(filepath):
        console.print(f"[red]文件不存在: {filepath}[/red]")
        return

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    chapters = re.split(r"### (?:第\d+章|番外)", text)
    names = re.findall(r"### ((?:第\d+章|番外)[^\n]*)", text)

    if not names:
        console.print("[yellow]未找到章节标题 (### 第N章 或 ### 番外X)[/yellow]")
        return

    table = Table(title=f"字数统计: {filepath}")
    table.add_column("章节", style="cyan")
    table.add_column("总字符", justify="right")
    table.add_column("汉字", justify="right")
    table.add_column("状态")

    total_hanzi = 0
    ok_count = 0
    for name, ch in zip(names, chapters[1:]):
        cleaned = re.sub(r"[#\-\*>\s]", "", ch)
        hanzi = len(re.findall(r"[一-鿿]", cleaned))
        total_hanzi += hanzi

        if len(cleaned) >= threshold:
            status = "[green]OK[/green]"
            ok_count += 1
        elif len(cleaned) >= threshold * 0.5:
            status = "[yellow]--[/yellow]"
        else:
            status = "[red]SHORT[/red]"

        table.add_row(name, str(len(cleaned)), str(hanzi), status)

    table.add_row(
        "[bold]总计[/bold]",
        "",
        f"[bold]{total_hanzi}[/bold]",
        f"[bold]{ok_count}/{len(names)} 达标[/bold]",
    )

    console.print(table)


# ── stats ─────────────────────────────────────────────

@main.command()
@click.option("--db", default=None, help="Index DB path")
@click.pass_context
def stats(ctx, db):
    """Show corpus index statistics."""
    import sqlite3

    cfg: Config = ctx.obj["cfg"]
    db_path = db or os.path.join(cfg.index_dir, "corpus.db")

    if not os.path.exists(db_path):
        console.print(f"[red]索引数据库不存在: {db_path}[/red]")
        return

    conn = sqlite3.connect(db_path)

    total = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    anchor_count = conn.execute(
        "SELECT COUNT(*) FROM passages WHERE is_anchor = 1"
    ).fetchone()[0]

    avg_score = conn.execute(
        "SELECT AVG(score) FROM passages"
    ).fetchone()[0] or 0

    table = Table(title="语料库统计")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("总段落数", str(total))
    table.add_row("锚点段落数", str(anchor_count))
    table.add_row("平均技法得分", f"{avg_score:.1f}")
    table.add_row("DB 路径", db_path)

    console.print(table)

    # Per-play-type breakdown
    from .corpus_indexer import PLAY_PATTERNS
    play_table = Table(title="玩法类型分布")
    play_table.add_column("玩法", style="cyan")
    play_table.add_column("段落数", justify="right")
    play_table.add_column("占比", justify="right")

    for pt in PLAY_PATTERNS:
        count = conn.execute(
            "SELECT COUNT(*) FROM passages WHERE play_types LIKE ?", (f"%{pt}%",)
        ).fetchone()[0]
        if count > 0:
            play_table.add_row(pt, str(count), f"{count/total*100:.1f}%" if total else "0%")

    conn.close()
    console.print(play_table)


if __name__ == "__main__":
    main()
