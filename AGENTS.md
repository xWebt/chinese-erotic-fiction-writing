# AGENTS.md — Chinese Erotic Fiction Writing Toolkit

White-paper toolkit for Chinese adult (H) fiction. Full instructions in `CLAUDE.md`.

## Quick Start

```bash
pip install -e .
```

## What This Toolkit Does

**Write fiction**: Read `CLAUDE.md` for the full methodology. Core rule: investigate preferences BEFORE writing — every user is a blank page.

**Index a corpus**: `novel index -d <dir>` scans local .txt novel collections. Quality filters, technique scoring, play-type classification → SQLite.

**Calibrate quality**: `novel calibrate -a <anchor_file>` computes technique baselines from known-good works.

**Count words**: `novel wordcount <file>` — per-chapter stats with pass/fail.

**Discover plays**: The Agent reads prompt templates from `harness/prompt_templates.py`, samples indexed corpus passages, and uses its own LLM to discover play patterns and extract atomic templates.

**Cross-combine plays**: Agent uses combine prompts to fuse playbook templates into novel variants.

## Privacy (P0)

- `sessions/` is `.gitignore`d — never leaves the user's machine
- All reference files de-personalized — no real character/scene names in repo
- Each user's kinks, characters, and play preferences are local only

## Three-Layer Architecture

| Layer | What | Public |
|---|---|---|
| L1 Universal | `SKILL.md` + `references/` — pure technique | Yes |
| L2 Accumulated | Anonymous cross-user patterns | Yes |
| L3 Sessions | `sessions/` — per-user capsule (prefs + feedback + style fingerprint) | **No** |

## Session Learning

Each session makes the skill smarter for that user:
1. First use → investigate → create capsule
2. Returning → read capsule → skip basics
3. Feedback → append log → update style fingerprint
4. Satisfied passages → extract density → auto-match next time
5. Over time → fingerprint converges to user's taste

## Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Complete agent instructions |
| `SKILL.md` | Skill definition + session learning spec |
| `references/carnal-writing-techniques.md` | High-density technique reference |
| `references/quiet-exposure-techniques.md` | Exhibitionism playbook template (example) |
| `scripts/wordcount.py` | Per-chapter word counter |
| `scripts/batch_insert.py` | Anchor-based text insertion |
| `harness/prompt_templates.py` | LLM prompt templates |
| `harness/cli.py` | CLI entry (local tools only) |

## Core Rules

1. **White paper**: Nothing pre-bound — all preferences from investigation
2. **Body first**: Show through sensation, not narration
3. **Sound + liquid**: Always paired, never dry
4. **Multi-dimensional**: Each body part across 3-4 dimensions
5. **Climax full chain**: Never one sentence
