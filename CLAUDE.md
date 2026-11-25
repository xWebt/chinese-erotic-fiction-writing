# Agent Instructions

## Priority

1. User requirements and taboos.
2. `SKILL.md`.
3. `core/prose-rules.md`.
4. `styles/plain-modern.yaml`.
5. One playbook and at most one optional module.

Do not load the whole repository before writing.

## Runtime

- `core/` contains reusable writing rules.
- `styles/` contains corpus-derived style fingerprints.
- `playbooks/` contains one-scene structure cards.
- `harness/` contains local profiling and audit tools.
- Legacy long-form references are removed.

## Investigation

When details are missing, infer:

- adults, consensual;
- third-person limited;
- modern setting;
- `plain-modern` style;
- no fixed word count.

Ask only when taboo, POV, existing characters, or explicit style references make the scene ambiguous.

## Scene Contract

Every scene must contain:

- POV;
- want;
- obstacle;
- tactic;
- turn;
- consequence.

If a scene does not change information, distance, power, risk, relationship, or next action, rewrite it.

## Voice

- Modern spoken Chinese.
- Concrete action and dialogue before explanation.
- Never use signs, screens, or narration as an instruction card.
- Do not chain nodding, pointing, turning and walking in one paragraph.
- Do not use consecutive short narrative paragraphs for fake rhythm.
- Sparse metaphor from POV experience.
- End on a thing that happened, not an epiphany.

## Intimacy

- Adults only.
- Explicit, revocable consent.
- Body detail is selective, not a checklist.
- No mandatory sound/liquid pair.
- No fixed climax chain.
- Aftermath must change something concrete.

## Corpus Work

- `novel styleprofile` for aggregate metrics.
- `novel scenes` for at most six bounded scene windows.
- Never dump whole books into context.
- Never copy source text into public files.
- Keep local paths and titles out of public artifacts when not needed.

## Editing

- Preserve unrelated user changes.
- Use batch edits for repository work.
- Keep `SKILL.md` an entry point, not a manual.
- Add details to `core/` or one playbook rather than duplicating rules.
- Test with `python -m unittest discover -s tests -v`.

## Token Discipline

- One primary style, one optional module, one playbook.
- One style audit on the complete draft.
- One targeted revision pass.
- Do not narrate every tool call.
- Separate project maintenance from fiction writing threads.

## Privacy

`sessions/`, corpora, manuscripts and local file paths stay local. Public profiles contain only abstract metrics and de-identified notes.
