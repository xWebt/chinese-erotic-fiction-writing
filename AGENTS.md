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
- `references/`: archived legacy notes; never load them by default.
- `harness/`: profiling, scene extraction, style audit and token audit.
- `tests/`: unit and contract tests.

## Rules

- Keep `SKILL.md` under roughly 4,000 Chinese characters.
- Do not expand or auto-load legacy references; keep them archived only.
- Do not add generic body-detail checklists.
- Default context: adults and mutual participation. Do not add verification boilerplate.
- Privacy: no local paths or source excerpts in public profiles.
- Prefer one batch edit over many tiny patches.

## Test

```bash
python -m unittest discover -s tests -v
novel stylecheck <sample.txt> --profile plain-modern
```

Also validate style and playbook YAML when PyYAML is available.
