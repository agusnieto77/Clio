# Contributing to Clio

Thanks for your interest in improving Clio.

This repository is designed for **research use with reproducible outputs**. That means contributions are welcome, but they should preserve three core properties:

1. **Determinism**
2. **Filesystem-based resumability**
3. **Validation between stages**

## Quick path

1. Fork the repository.
2. Create a branch for one focused change.
3. Run the regression suite.
4. Keep changes small and well scoped.
5. Open a pull request with a clear description of what changed and why.

## What kinds of contributions are useful

- Bug fixes in the deterministic harness (`harness/tools/`)
- Documentation improvements
- Better validation and error reporting
- New tests and regression coverage
- UI / readability improvements in generated reports
- Safer or clearer OpenCode agent prompts and skills

## What to avoid

- Mixing multiple unrelated changes in one PR
- Adding non-deterministic behavior without a strong reason
- Hiding failures instead of surfacing them clearly
- Breaking the expected folder contract under `Fuentes/`
- Removing validation steps just to make the pipeline "more permissive"

## Repository map

| Area | Purpose |
|------|---------|
| `harness/tools/` | Deterministic Python CLI tools |
| `.opencode/agents/` | Agent definitions |
| `.opencode/skill/` | Protocol skills with exact steps |
| `tests/` | Regression suite |
| `Fuentes/` | Example corpus structure |
| `docs/` | User-facing documentation |

## Before you change code

Please read:

- `README.md`
- `docs/uso.md`
- `docs/formato-del-corpus.md`

If your change touches the pipeline logic, also inspect the relevant scripts in `harness/tools/` and the associated skill in `.opencode/skill/`.

## Verification expectations

At minimum, contributors should run:

```bash
python tests/run_all.py
```

If your change touches a specific pipeline stage, also run the corresponding validation command(s), for example:

```bash
python harness/tools/validar.py transcripciones Fuentes/Actas
python harness/tools/validar.py metricas Fuentes/Actas
python harness/tools/validar.py informes Fuentes/Actas
```

## Pull request guidance

Please keep PRs easy to review.

### Good PR shape

- one focused concern
- clear motivation
- explicit verification steps
- note any intentional non-goals

### Helpful PR template structure

```markdown
## What changed

## Why it changed

## How to verify

## Out of scope
```

## Data and example corpora

Be careful with source material.

- Do not add archival material unless it is safe to publish.
- If you include examples, prefer material already approved for public redistribution.
- Avoid adding sensitive, restricted, or ambiguous-source documents.

## Style expectations

- Lead with the answer.
- Prefer small, explicit functions.
- Preserve deterministic behavior.
- Use the existing single sources of truth instead of duplicating constants or helpers.
- When in doubt, add a regression test.

## Next step

If you are unsure whether a change fits Clio's philosophy, open an issue first and describe the proposed change before implementing it.
