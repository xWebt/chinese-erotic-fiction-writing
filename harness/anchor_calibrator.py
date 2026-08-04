"""Anchor calibrator: extract technique baselines from known-good works.

Uses the named anchor works to compute reference distributions for:
- Technique density per dimension
- Passage length norms
- Play type distributions
- Vocabulary richness

These baselines are used to calibrate quality thresholds for the full corpus.
"""

import json
import sqlite3
from pathlib import Path
from collections import Counter

from rich.console import Console
from rich.table import Table

console = Console()


def calibrate(db_path: str, anchor_names: list[str]) -> dict:
    """Compute baseline metrics from anchor works in the index.

    Args:
        db_path: Path to SQLite index DB.
        anchor_names: List of anchor file name substrings to match.

    Returns:
        Dict with baseline metrics.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Build LIKE clauses for anchor matching
    clauses = " OR ".join(["file_path LIKE ?" for _ in anchor_names])
    params = [f"%{name}%" for name in anchor_names]

    rows = conn.execute(
        f"SELECT * FROM passages WHERE ({clauses}) AND score > 0", params
    ).fetchall()

    conn.close()

    if not rows:
        console.print("[yellow]警告: 未在索引中找到锚点作品段落。请先运行索引。[/yellow]")
        return {}

    console.print(f"锚点段落样本: [bold]{len(rows)}[/bold] 段")

    # Compute metrics
    scores = []
    dimensions = Counter()
    play_types = Counter()
    char_counts = []

    for row in rows:
        scores.append(row["score"])
        try:
            bd = json.loads(row["score_breakdown"])
            for k, v in bd.items():
                dimensions[k] += v
        except (json.JSONDecodeError, TypeError):
            pass
        for pt in row["play_types"].split(","):
            if pt.strip():
                play_types[pt.strip()] += 1
        char_counts.append(row["char_count"])

    n = len(scores)
    scores.sort()

    # Averages
    for k in dimensions:
        dimensions[k] = round(dimensions[k] / n, 2)

    baseline = {
        "sample_count": n,
        "score_avg": round(sum(scores) / n, 1),
        "score_median": scores[n // 2],
        "score_p25": scores[n // 4],
        "score_p75": scores[3 * n // 4],
        "dimension_averages": dict(dimensions),
        "char_count_avg": int(sum(char_counts) / n),
        "char_count_range": (min(char_counts), max(char_counts)),
        "top_play_types": play_types.most_common(15),
    }

    # Display
    table = Table(title="锚点作品技法基线")
    table.add_column("指标", style="cyan")
    table.add_column("值", style="green")

    table.add_row("样本数", str(baseline["sample_count"]))
    table.add_row("平均得分", str(baseline["score_avg"]))
    table.add_row("中位得分", str(baseline["score_median"]))
    table.add_row("P25/P75", f"{baseline['score_p25']} / {baseline['score_p75']}")
    table.add_row("平均段落长度(字)", str(baseline["char_count_avg"]))

    for dim, val in baseline["dimension_averages"].items():
        table.add_row(f"  维度 [{dim}]", str(val))

    table.add_row("高频玩法", ", ".join(f"{p}({c})" for p, c in baseline["top_play_types"][:5]))

    console.print(table)

    # Save baseline to JSON
    return baseline


def set_thresholds(baseline: dict, strictness: float = 0.5) -> dict:
    """Derive quality thresholds from anchor baseline.

    Args:
        baseline: Output from calibrate().
        strictness: 0.0 (loose) to 1.0 (strict). Default 0.5 uses median as min.

    Returns:
        Dict of threshold values.
    """
    if not baseline:
        return {}

    # Use percentile-based thresholds
    if strictness <= 0.3:
        score_min = baseline["score_p25"]
    elif strictness <= 0.7:
        score_min = baseline["score_median"]
    else:
        score_min = baseline["score_p75"]

    dim_thresholds = {}
    for dim, avg in baseline["dimension_averages"].items():
        dim_thresholds[dim] = max(0.5, round(avg * strictness, 1))

    return {
        "min_passage_score": max(3, int(score_min)),
        "min_char_count": max(100, baseline["char_count_avg"] // 3),
        "dimension_minimums": dim_thresholds,
    }
