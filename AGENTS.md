# AGENTS.md — Chinese Erotic Fiction Writing Toolkit

This repo is a toolkit for writing Chinese adult (H) fiction. Full instructions in `CLAUDE.md`.

## Quick Start

Install the harness CLI:
```bash
pip install -e .
```

## What You Can Do Here

**Write fiction**: Read `CLAUDE.md` for the full methodology. Key rule: investigate user preferences BEFORE writing — never assume defaults.

**Index a corpus**: `novel index` scans local .txt novel collections, filters by quality, scores technique density, and builds a searchable SQLite index.

**Discover play patterns**: `novel extract` uses LLM to scan the indexed corpus and identify play types (露出/调教/偷情/etc.), extracting atomic templates with iron rules, escalation axes, and scene templates as shareable YAML files.

**Cross-combine plays**: `novel combine` merges playbook templates to create novel variants. Use `novel combine --suggest` to get LLM recommendations.

**Generate chapters**: `novel generate -p "露出,古风" -s "御花园" -w 5000` — DeepSeek API-powered, segmented generation with auto-continue until word count target is met.

**Count words**: `novel wordcount <file>` — per-chapter word count with pass/fail threshold.

## Core Principles

1. **Investigation-driven**: Play type, voice, word count, genre — all determined per user, never hardcoded.
2. **Body first**: Show through sensation, not narration.
3. **Sound + liquid**: Always paired, never dry action.
4. **Multi-dimensional**: Each body part described across 3-4 dimensions.
5. **Climax fleshed out**: Full body reaction chain, never one sentence.

## Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Complete agent instructions |
| `SKILL.md` | Claude Code skill definition |
| `references/carnal-writing-techniques.md` | High-density writing techniques |
| `references/quiet-exposure-techniques.md` | Exhibitionism play example |
| `scripts/wordcount.py` | Per-chapter word counter |
| `scripts/batch_insert.py` | Anchor-based batch text insertion |
| `harness/` | Python CLI tool modules |

## Configuration

All config via `~/.fiction-harness/config.yaml` or environment variables (`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`). No hardcoded paths in source.

## P0 Design Rule

This toolkit does NOT bind to any fixed play type, author voice, or word count. All preferences are investigation outputs, not built-in defaults. The example content marked 「当前用户〔男〕」 is from a previous user and must NOT be assumed for new users.
