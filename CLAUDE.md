# Chinese Erotic Fiction Writing — Agent Instructions

This repo is a **white-paper toolkit** for writing Chinese adult (H) fiction.
It provides methodology, not defaults. Every user opens a blank page.

## Architecture (Three Layers)

| Layer | Location | Content | Public? |
|---|---|---|---|
| L1 Universal | `SKILL.md` + `references/` | Pure technique methodology | Yes |
| L2 Accumulated | `references/` (de-personalized) | Cross-user pattern extraction | Yes |
| L3 Session Capsule | `sessions/` (local only) | Per-user preferences, feedback log, style fingerprint | **Never** |

## Privacy Design (P0)

- `sessions/` is in `.gitignore` — never committed, never pushed
- All reference files are de-personalized (角色名 → [女主]/[男主], 场景 → [地点])
- Each user's kinks, characters, and play preferences stay local
- The GitHub repo contains zero user identities

## Mandatory Investigation (FIRST thing for any new user)

Ask these questions before writing anything. Never assume defaults:

1. **Gender / Voice**: Male → direct, raw (器官直呼名). Female → atmospheric, sensual. Ask if unsure.
2. **Play Types & Taboos**: What kinks? What's forbidden? Record taboos as hard constraints.
3. **Genre & Format**: Setting, perspective, H-scene ratio, words per chapter.
4. **Style References**: Any reference works to learn from?

Save results to `sessions/{user_id}.yaml`. Re-read this file on subsequent sessions.

## Session Capsule (The Learning Loop)

Each session makes the skill smarter for that specific user:

1. **First use** → investigation → create capsule → write preferences
2. **Returning** → read capsule → skip basics → ask "what's new this time?"
3. **Feedback received** → parse the correction → append to feedback_log → update style_fingerprint
4. **Passage satisfied** → extract technique density → update fingerprint → next gen auto-matches
5. **Over time** → feedback_log = personalized pitfall list → fingerprint converges to user's taste

Capsule structure is documented in `SKILL.md` session learning section.

## Core Writing Rules

- **Body first**: 发烫/战栗/湿透/咬唇/腿软/收缩/喷水/脚趾蜷缩. Show, don't narrate.
- **Orgasm full chain**: 痉挛 → 弓起 → 脚尖绷直 → 收缩 → 喷涌 → 眼前发白 → 脱力. Never one line.
- **Sound + liquid always paired**: 啧啧/咕叽/噗嗤 + 汩汩/顺着淌. No "dry action."
- **Multi-dimensional**: Each body part across 3-4 dimensions (shape/touch/sound/sight/state). See `references/carnal-writing-techniques.md`.
- **Organ naming per investigation**: No default terms. Ask first.
- **Minimal filler**: 2-3 lines for scene setting, then straight to H/body/psychology.
- **Chapter structure**: Intro (2-3 lines) → setup → H body (2-4 rounds) → climax → hook.

## Local Tools (harness/ CLI)

Pure local operations, no API dependency:

- `novel index -d <corpus_dir>` — Scan .txt novel library, build searchable index
- `novel calibrate -a <anchor_file> ...` — Calibrate quality thresholds from known-good works
- `novel wordcount <file>` — Per-chapter word count
- `novel stats` — Index statistics

Install: `pip install -e .`

## Prompt Templates

`harness/prompt_templates.py` contains structured prompts for:
- Play type discovery from corpus passages
- Atomic playbook extraction (iron rules + escalation axes + scene templates)
- Cross-combining playbooks into novel variants
- Chapter outline and scene generation
- Style reference injection

The Agent reads these templates and executes them with its own LLM backend.

## Key Workflows

### Revision
Sync feedback → update outline → regenerate → self-review → deliver. Never patch.

### Multi-session writing
Maintain `进度.txt` in the output directory. Update at each session end, read first on resume.

### Batch expansion
Use `scripts/batch_insert.py`. Anchor = unique original sentence (20-60 chars). Insert in descending order. Verify with `novel wordcount` after each round.

## Reference Files

All reference files are de-personalized technique templates extracted from corpus (no real names/paths).
- `references/carnal-writing-techniques.md` — High-density technique: organ dimensions, sound/liquid pairing, climax chains
- `references/quiet-exposure-techniques.md` — Exhibitionism (悄悄露出): near-miss exposure tension
- `references/tech-toy-play-techniques.md` — Sex toys / remote control: edge-play & power of the dial
- `references/domination-training-techniques.md` — Dom/sub (调教): orgasm-permission system & reward/punish loop
- `references/group-play-techniques.md` — Group / orgy: spatial choreography & role division

## Critical Pitfalls

- **White paper rule (P0)**: Never bind to any play type, voice, or word count. Everything from investigation.
- Don't deliver half-finished work. Self-review: climax count, chapter numbering, pronoun consistency.
- Environment/setup ≤ 40% per chapter.
- When expanding: ADD new content, don't rephrase existing.
- Person pronoun consistency: 她/他/朕/本王 get mixed during insertion. Proofread.
- Anchor nesting: never use previously-inserted text as new anchor.
- Never use large-block patch (over half chapter). Patch only for ≤200 char insertions.
