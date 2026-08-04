# Chinese Erotic Fiction Writing — AI Agent Instructions

This repo is a comprehensive toolkit for writing Chinese adult (H) fiction. It provides:
- **Writing methodology** — rules, templates, pitfalls (see `references/`)
- **Harness CLI** — Python tools for corpus indexing, play pattern extraction, chapter generation (see `harness/`)
- **Batch scripts** — word counting, anchor-based passage insertion (see `scripts/`)

## When to Use This Toolkit

- User asks to write / expand / rewrite Chinese H fiction
- User provides an outline and wants it fleshed out
- User complains output is too short / not erotic enough / too much filler
- User wants to analyze their local novel corpus for play patterns

## Mandatory Investigation (do this FIRST for any new user)

Every user has different preferences. Never assume defaults. Before writing anything, ask:

1. **Gender / author voice**: Male user → raw, direct male voice (器官直呼名: 骚穴/大奶/肉棒). Female user → atmosphere-first, sensual, psychological. If unsure, ask.
2. **Play type / kink**: Exhibitionism? BDSM? Group? Pure love? Infidelity? Uniform? Record preferences and TABOOS.
3. **Genre & format**: Historical? Modern? Xianxia? First or third person? H-scene ratio? Words per chapter target.
4. **Style references**: Any reference works? Use `scripts` phrase extraction to learn their style.
5. Save investigation results to session memory. If results conflict with any pre-existing preferences, investigation wins.
6. This investigation also applies to batch expansion of existing novels.

## Core Writing Rules (applies regardless of play type)

- **Body reaction first**: 发烫/战栗/湿透/咬唇/腿软/收缩/喷水/脚趾蜷缩 — show through body, don't narrate.
- **Orgasm must be fleshed out**: 痉挛 → 弓起 → 脚尖绷直 → 收缩 → 喷涌 → 眼前发白 → 脱力. Never one-line it.
- **Sound + liquid always together**: 啧啧/咕叽咕叽/噗嗤噗嗤 + 汩汩/顺着大腿根往下淌.
- **Multi-dimensional description**: Breasts — shape/touch/nipple changes/deformation/sucking reaction. Pussy — labia/clitoris/entrance/juices/contraction. At least 3-4 dimensions per scene.
- **Organ naming follows investigation**: Male voice → direct (骚穴/大奶/肉棒/浓精). Female voice → softer terms possible.
- **Minimal environmental filler**: 2-3 sentences to set scene, then straight to H/body/psychology.
- **Chapter fullness**: Respect word count target. When asked to "expand", actually add new content, don't rephrase existing.
- **Delivery format**: Plain markdown, chapter title then body, end with hook. No changelog in files.

## Chapter Structure

```
Scene intro (2-3 lines) → Setup / tension planting → H main body (2-4 rounds, fully fleshed) → Climax resolution → Ending hook (tease next chapter)
```

For word count guarantee: break each chapter into 3-4 scene segments, 1200-2000 words each, with a "detail checklist" of must-include keywords/actions per chapter.

## Using the Harness CLI

The `novel` tool provides automated assistance. Install with `pip install -e .` from the repo root.

### `novel init`
First-time setup. Prompts for DeepSeek API key and corpus directory. Writes `~/.fiction-harness/config.yaml`.

### `novel index`
Scan the local novel corpus, build a searchable SQLite index with quality filtering and play-type classification.

### `novel calibrate`
Compute technique density baselines from anchor works. Calibrates scoring thresholds.

### `novel extract`
LLM-driven discovery: scan indexed corpus → identify play types → extract atomic templates (iron rules + escalation axis + scene templates + sentence banks) as shareable YAML files.

### `novel combine`
Cross-combine playbook templates to create novel play variants. Use `--suggest` to get LLM recommendations for interesting combinations.

### `novel generate`
Generate a full chapter using DeepSeek API:
- Generates a scene-segmented outline
- Generates each scene independently (3-4 segments)
- Auto-continues any segment that falls short of word target (up to 4 rounds)
- Optionally injects style references from indexed corpus

Example: `novel generate -p "露出,古风" -s "御花园假山后" -w 5000 -c "女主媚儿, 男主燕凌霄"`

### `novel wordcount`
Count words per chapter in a markdown novel file.

### `novel stats`
Show corpus index statistics.

## Key Workflows

### Revision workflow
When user gives feedback: sync suggestions to outline → delete old text → rebuild from outline → self-review → deliver.

### Multi-session writing
Maintain `接续进度.md` (progress tracking file) in the workspace. Update at end of each session. Read it first when resuming. 2-3 chapters per session.

### Batch expansion (anchored insertion)
Built into `scripts/batch_insert.py`. Use when expanding multiple chapters from skeleton to target word count. Key rules:
- Anchors must be unique full sentences from ORIGINAL text (20-60 chars), never from previously inserted text
- Insert in descending position order
- Verify with `wordcount.py` after each round
- Never use `patch` for content containing quotes — use `write_file` for standalone Python scripts instead

## Reference Files

- `references/carnal-writing-techniques.md` — High-density carnal writing techniques extracted from reference works
- `references/quiet-exposure-techniques.md` — Quiet/public exhibitionism play template (example, don't assume it applies to all users)

## Critical Pitfalls

- **P0 design principle**: This toolkit must NOT bind to any specific play type, voice, or word count. Everything is investigation-driven.
- Don't deliver half-finished work — self-review before showing user
- Outline chapter numbers must match body text
- Environmental/setup content ≤ 40% per chapter
- When expanding, actually ADD new paragraphs, don't rewrite same text
- Person pronoun consistency: 她/他/朕/本王 frequently get mixed up during insertion — proofread
- Never use large-block patch replacements (over half a chapter)
- Anchor nesting: never use text containing old anchors as new insertions
