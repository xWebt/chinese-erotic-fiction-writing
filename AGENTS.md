# AGENTS.md

Repository-level instructions for coding agents.

## Read

- `SKILL.md` is the entry point.
- Writing uses `core/prose-rules.md`, `styles/plain-modern.yaml`, and one playbook.
- Do not preload all styles or playbooks.

## Architecture

- `core/`: scene, prose, intimacy, revision and context rules.
- `styles/`: corpus-derived profiles.
- `playbooks/`: one-scene structure cards.
- `harness/`: profiling, scene extraction, style audit and token audit.
- `tests/`: unit and contract tests.

## Rules

- Keep `SKILL.md` under roughly 4,000 Chinese characters.
- Do not reintroduce a monolithic references directory.
- Do not add generic body-detail checklists.
- Safety: adults, explicit consent, user taboos.
- Privacy: no local paths or source excerpts in public profiles.
- Prefer one batch edit over many tiny patches.

## Test

```bash
python -m unittest discover -s tests -v
novel stylecheck <sample.txt> --profile plain-modern
```

Also validate style and playbook YAML when PyYAML is available.
