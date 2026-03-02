# Phase 2 Roadmap

Deferred modules:
- Journal
- Opinions
- Curiosity

## Backward compatibility rule
Do not rename existing v1 section headers in `compiled_context.md`.

## Planned folder additions
- `Journal/`
- `Opinions/`
- `Curiosity/`

## Planned output additions
Append new sections after section 8:
- 9. Journal Snapshot
- 10. Opinion Evolution
- 11. Curiosity Queue

## Migration approach
1. Detect missing new folders gracefully.
2. Keep compiler functional for v1 vaults.
3. Emit warnings (not hard failures) for absent phase-2 modules.
