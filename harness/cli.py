"""CLI entry point for the Chinese fiction writing harness.

Pure local tools — no API dependency, no configuration file needed.
Commands:
    novel index       Build corpus index from .txt files
    novel styleprofile  Summarize prose style from local text files
    novel scenes        Extract diverse bounded scenes for close reading
    novel tokenaudit    Audit Codex session token use
    novel calibrate   Compute anchor baseline
    novel stylecheck  Audit prose rhythm and AI-tone risks
    novel wordcount   Count words in a file
    novel stats       Show corpus index statistics
"""

import click
from rich.console import Console

console = Console()


@click.group()
def main():
    """Chinese Fiction Harness — local tools for novel writing assistance."""


# ── tokenaudit ────────────────────────────────────────

@main.command()
@click.argument("session_file")
@click.option("--budget", type=int, default=1_000_000, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Print JSON")
def tokenaudit(session_file, budget, as_json):
    """Summarize exact token usage from a Codex JSONL session."""
    from rich.table import Table
    from .token_audit import audit_session, to_json

    report = audit_session(session_file, budget=budget)
    if as_json:
        click.echo(to_json(report))
        return
    if error := report.get("error"):
        raise click.ClickException(error)

    table = Table(title="Session Token Use")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Responses", str(report["responses"]))
    for key, value in report["thread"].items():
        table.add_row(key, f"{value:,}")
    table.add_row("context overhead", f"{report['overhead_ratio']:.1%}")
    table.add_row("visible output", f"{report['output_ratio']:.1%}")
    console.print(table)
    for warning in report["warnings"]:
        console.print(f"[yellow]{warning}[/yellow]")


# ── scenes ────────────────────────────────────────────

@main.command()
@click.argument("filepath")
@click.option("--count", type=int, default=6, show_default=True)
@click.option("--chars", type=int, default=1200, show_default=True)
def scenes(filepath, count, chars):
    """Extract complete bounded scenes for corpus-style close reading."""
    from .scene_sampler import render_scenes, sample_file

    sampled = sample_file(filepath, count=count, target_chars=chars)
    if not sampled:
        raise click.ClickException("No usable scenes found")
    click.echo(render_scenes(sampled))


# ── styleprofile ──────────────────────────────────────

@main.command()
@click.argument("paths", nargs=-1, required=True)
@click.option("--limit", type=int, default=30, show_default=True)
@click.option("--json", "as_json", is_flag=True, help="Print JSON")
def styleprofile(paths, limit, as_json):
    """Summarize prose rhythm from local .txt files or directories."""
    from rich.table import Table
    from .corpus_style import profile_paths, to_json

    report = profile_paths(paths, limit=limit)
    if as_json:
        click.echo(to_json(report))
        return

    if not report.get("sample_count"):
        raise click.ClickException("No usable .txt samples found")

    table = Table(title=f"Corpus Style Profile ({report['sample_count']} samples)")
    table.add_column("Metric", style="cyan")
    table.add_column("P25", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("P75", justify="right")
    for key, values in report.items():
        if isinstance(values, dict) and {"p25", "median", "p75"} <= values.keys():
            table.add_row(key, str(values["p25"]), str(values["median"]), str(values["p75"]))
    console.print(table)
    console.print("[dim]Use the summary first; inspect at most 3 short excerpts.[/dim]")


# ── index ─────────────────────────────────────────────

@main.command()
@click.option("--corpus-dir", "-d", required=True, help="Corpus .txt directory")
@click.option("--db", default=None, help="Output SQLite DB path (default: ./corpus.db)")
@click.option("--anchor", "-a", multiple=True, help="Anchor work file name patterns")
@click.option("--min-score", default=2, help="Minimum technique score to keep (default: 2)")
def index(corpus_dir, db, anchor, min_score):
    """Build corpus index from local .txt novel files.

    Walks the corpus directory, auto-detects encoding (UTF-8/GBK),
    filters low-quality content, deduplicates, scores retrieval signals,
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
    """Compute retrieval-signal baseline from anchor works.

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
        with open(output, "w", encoding="utf-8") as f:
            json.dump({"baseline": baseline, "thresholds": thresholds}, f, ensure_ascii=False, indent=2)
        console.print(f"[green]Baseline saved to {output}[/green]")


# ── wordcount ─────────────────────────────────────────

@main.command()
@click.argument("filepath")
@click.option("--threshold", "-t", type=int, default=5000, help="Pass threshold (default: 5000)")
def wordcount(filepath, threshold):
    """Count words per chapter in a novel file (.txt or markdown)."""
    import re
    import os
    from rich.table import Table

    if not os.path.exists(filepath):
        raise click.ClickException(f"File not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    # Accept both plain-text (第N章 XXX) and markdown (### 第N章 XXX) headers,
    # matching the .txt delivery format used by the writing workflow.
    # 番外 requires digits and/or a delimiter (：or :) so bare "番外" in body
    # text is not mistaken for a header; split/name regexes stay consistent.
    title_re = r"(?:###\s*)?(?:第\d+章|番外[一二三四五六七八九十\d]*[：:])"
    chapters = re.split(title_re, text)
    names = re.findall(r"(?:###\s*)?((?:第\d+章|番外[一二三四五六七八九十\d]*[：:])[^\n]*)", text)

    if not names:
        # Fallback: Chinese-numeral chapter titles (第一章/第十二章) at line start.
        chapters = re.split(r"(?:^|\n)(?:第[一二三四五六七八九十\d]+章)", text)
        names = re.findall(r"(?:第[一二三四五六七八九十\d]+章[^\n]*)", text)

    if not names:
        raise click.ClickException("No chapter titles found (第N章 / ### 第N章 / 番外X / 第一章)")

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


# ── stylecheck ────────────────────────────────────────

@main.command()
@click.argument("filepath")
@click.option("--json", "as_json", is_flag=True, help="Print the full report as JSON")
@click.option("--profile", "profile_id", default=None, help="Compare against a style profile")
def stylecheck(filepath, as_json, profile_id):
    """Audit prose for AI-tone risks and repetitive sentence patterns."""
    import os
    from rich.table import Table
    from .style_audit import audit_text, report_to_json

    if not os.path.exists(filepath):
        raise click.ClickException(f"File not found: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        text = f.read()

    report = audit_text(text)
    if profile_id:
        from .style_profiles import evaluate_profile, load_style

        report["profile_findings"] = evaluate_profile(report, load_style(profile_id))
        report["warnings"].extend(report["profile_findings"])
    if as_json:
        click.echo(report_to_json(report))
        return

    summary = report["summary"]
    risk = summary["risk_level"]
    risk_color = {"low": "green", "moderate": "yellow", "high": "red"}[risk]
    overview = Table(title=f"Style Audit: {filepath}")
    overview.add_column("Metric", style="cyan")
    overview.add_column("Value", style="green")
    overview.add_row("Risk score", f"{summary['risk_score']}/100")
    overview.add_row("Risk level", f"[{risk_color}]{risk}[/{risk_color}]")
    overview.add_row("Characters", str(summary["char_count"]))
    overview.add_row("Sentences", str(summary["sentence_count"]))
    overview.add_row("Dialogue share", f"{summary['dialogue_ratio']:.1%}")
    overview.add_row("Mean sentence length", str(report["sentence_stats"]["mean"]))
    overview.add_row("Sentence length stdev", str(report["sentence_stats"]["stdev"]))
    overview.add_row("Metaphor / 1k chars", str(report["style_markers"]["metaphor_per_1000_chars"]))
    overview.add_row("AI elevation hits", str(sum(report["ai_elevation_patterns"].values())))
    overview.add_row("Purple-prose hits", str(report["style_markers"]["purple_prose_count"]))
    overview.add_row("Prop exposition hits", str(report["style_markers"]["prop_exposition_count"]))
    overview.add_row("Max action chain", str(report["style_markers"]["max_action_chain"]))
    overview.add_row("Max short narrative run", str(report["style_markers"]["max_short_narrative_run"]))
    console.print(overview)

    if report["warnings"]:
        warnings = Table(title="Risk Signals")
        warnings.add_column("Level", style="cyan", no_wrap=True)
        warnings.add_column("Signal", style="magenta", no_wrap=True)
        warnings.add_column("Revision cue", style="white")
        for warning in report["warnings"]:
            level = warning["level"]
            level_color = {"low": "green", "medium": "yellow", "high": "red"}[level]
            warnings.add_row(
                f"[{level_color}]{level}[/{level_color}]",
                warning["code"],
                warning["message"],
            )
        console.print(warnings)
    else:
        console.print("[green]No major prose-risk signals found.[/green]")

    console.print("[dim]Signals are revision prompts, not a literary verdict.[/dim]")


# ── stats ─────────────────────────────────────────────

@main.command()
@click.option("--db", default="corpus.db", help="Index DB path")
def stats(db):
    """Show corpus index statistics."""
    import os
    import sqlite3
    from rich.table import Table

    if not os.path.exists(db):
        raise click.ClickException(f"Index DB not found: {db}")

    conn = sqlite3.connect(db)
    total = conn.execute("SELECT COUNT(*) FROM passages").fetchone()[0]
    anchor_count = conn.execute("SELECT COUNT(*) FROM passages WHERE is_anchor = 1").fetchone()[0]
    avg_score = conn.execute("SELECT AVG(score) FROM passages").fetchone()[0] or 0

    t1 = Table(title="Corpus Statistics")
    t1.add_column("Metric", style="cyan")
    t1.add_column("Value", style="green")
    t1.add_row("Total passages", str(total))
    t1.add_row("Anchor passages", str(anchor_count))
    t1.add_row("Avg retrieval score", f"{avg_score:.1f}")
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
