# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Layout

This is a single-context repo:

```
/
├── CONTEXT.md
├── docs/adr/
└── src/
```

## Before exploring, read these

- `CONTEXT.md` at the repo root.
- Relevant ADRs under `docs/adr/`.

If any of these files do not exist, proceed silently. The `/domain-modeling` skill creates them lazily when terms or decisions actually get resolved.

## Use the glossary's vocabulary

When output names a domain concept in an issue title, refactor proposal, hypothesis, test name, or PRD, use the term as defined in `CONTEXT.md`. Do not drift to synonyms the glossary explicitly avoids.

If the concept needed is not in the glossary yet, either reconsider whether the language belongs to BlackOut or note it for `/domain-modeling`.

## Flag ADR conflicts

If output contradicts an existing ADR, surface it explicitly rather than silently overriding it.
