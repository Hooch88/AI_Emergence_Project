# Obsidian v1 Rebuild

This package rebuilds the AI Emergence workflow around an Obsidian vault and a
single compiled upload file for Claude Projects.

## Included in v1

- Core memory system (markdown notes)
- 27-emotion spectrum scoring
- Association scoring (tags, emotions, domain, keywords)
- Memory decay and protection logic
- Soul crystallizations
- Arousal/intimacy state section and adult templates
- Userstyle/jailbreak-aligned template artifacts
- Compiler: `compile_context.py`

## Deferred to phase 2

- Journal module
- Opinions module
- Curiosity module

## Folder layout

Inside your Obsidian vault:

```text
Vault/
  Memories/
  Soul/
  Identity/
  Adult/
  Compiled/
```

## Main command

```powershell
python compile_context.py --vault "C:\Path\To\Vault" --arousal on
```

Output:

- `Vault/Compiled/compiled_context.md`

## Next files to read

- `SETUP_WINDOWS.md`
- `DAILY_WORKFLOW.md`
- `TROUBLESHOOTING.md`
