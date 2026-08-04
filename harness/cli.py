"""CLI entry point for the Chinese fiction writing harness.

Pure local tools — no API dependency, no configuration file needed.
Commands:
    novel index       Build corpus index from .txt files
    novel calibrate   Compute anchor baseline
    novel wordcount   Count words in a file
    novel stats       Show corpus index statistics
"""

import click
from rich.console import Console

console = Console()


@click.group()
def main():
    """Chinese Fiction Harness — local tools for novel writing assistance."""


# ── index ─────────────────────────────────────────────

@main.command()
@click.option("--corpus-dir", "-d", required=True, help="Corpus .txt directory")
@click.option("--db", default=None, help="Output SQLite DB path (default: ./corpus.db)")
@click.option("--anchor", "-a", multiple=True, help="Anchor work file name patterns")
@click.option("--min-score", default=2, help="Minimum technique score to keep (default: 2)")
def index(corpus_dir, db, anchor, min_score):
    """Build corpus index from local .txt novel files.

    Walks the corpus directory, auto-detects encoding (UTF-8/GBK),
    filters low-quality content, deduplicates, scores technique density,
    classifies play types, and stores results in SQLite.
    """
    from .corpus_indexer import build_index

    db_path = db or "corpus.db"
    build_index(str(corpus_dir), db_path, list(anchor), min_score=min_score)


# ── calibrate ─────────────────────────────────────────

@main.command()
@click.option("--db", default="corpus.db", help="Index DB path")
@click.option("--anchor", "-a", multiple=True, required=True, help="Anchor file name patterns")
@click.option("--strictness", "-s", type=float, default=0.5, help="Threshold strictness 0-1 (default 0.5)")
@click.option("--output", "-o", default=None, help="Save baseline JSON")
def calibrate(db, anchor, strictness, output):
    """Compute technique density baseline from anchor works.

    Uses named anchor works to establish reference distributions for
    scoring thresholds across all technique dimensions.
    """
    from .anchor_calibrator import calibrate as do_calibrate, set_thresholds

    baseline = do_calibrate(db, list(anchor))
    if not baseline:
        return

    thresholds = set_thresholds(baseline, strictness)
    console.print(f"\nThresholds (strictness={strictness}):")
    for k, v in thresholds.items():
        console.print(f"  {k}: {v}")

    if output:
        import json
        with open(output, "w") as f:
            json.dump({"baseline": baseline, "thresholds": thresholds}, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Baseline saved to {output}[/green]")


# ── wordcount ─────────────────────────────────────────

@main.command()
@click.argument("filepath")
@click.option("--threshold", "-t", type=int, default=5000, help="Pass threshold (default: 5000)")
def wordcount(filepath, threshold):
    """Count words per chapter in a markdown novel file."""
    import re
    import os
    from rich.table import Table

    if not os.path.exists(filepath):
        console.print(f"[red]File not found: {filepath}[/red]")
        return

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    chapters = re.split(r"### (?:第\d+章|番外)", text)
    names = re.findall(r"### ((?:第\d+章|番外)[^\n]*)", text)

    if not names:
        console.print("[yellow]No chapter titles found (### 第N章 or ### 番外X)[/yellow]")
        return

    table = Table(title=f"Word Count: {filepath}")
    table.add_column("Chapter", style="cyan")
    table.add_column("Total Chars", justify="right")
    table.add_column("Chinese", justify="right")
    table.add_column("Status")

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

    table.add_row("[bold]Total[/bold]", "", f"[bold]{total_hanzi}[/bold]", f"[bold]{ok_count}/{len(names)} OK[/bold]")
    console.print(table)


# ── stats ─────────────────────────────────────────────

@main.command()
@click.option("--db", default="corpus.db", help="Index DB path")
def stats(db):
    """Show corpus index statistics."""
    import sqlite3
    from rich.table import Table

    if not __import__("os").path.exists(db):
        console.print(f"[red]Index DB not found: {db}[/red]")
        return

    conn = sqlite3.connect(db)
    total = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    anchor_count = conn.execute("SELECT COUNT(*) FROM passages WHERE is_anchor = 1").fetchone()[0]
    avg_score = conn.execute("SELECT AVG(score) FROM passages").fetchone()[0] or 0

    t1 = Table(title="Corpus Statistics")
    t1.add_column("Metric", style="cyan")
    t1.add_column("Value", style="green")
    t1.add_row("Total passages", str(total))
    t1.add_row("Anchor passages", str(anchor_count))
    t1.add_row("Avg technique score", f"{avg_score:.1f}")
    console.print(t1)

    from .corpus_indexer import PLAY_PATTERNS
    t2 = Table(title="Play Type Distribution")
    t2.add_column("Play Type", style="cyan")
    t2.add_column("Passages", justify="right")
    t2.add_column("Share", justify="right")

    for pt in PLAY_PATTERNS:
        count = conn.execute(
            "SELECT COUNT(*) FROM passages WHERE play_types LIKE ?", (f"%{pt}%",)
        ).fetchone()[0]
        if count > 0:
            t2.add_row(pt, str(count), f"{count/total*100:.1f}%")

    conn.close()
    console.print(t2)


if __name__ == "__main__":
    main()
