# TROUBLESHOOTING

## "compiled_context.md was not created"
- Confirm vault path is correct.
- Confirm `Compiled/` exists in the vault.
- Re-run command and read warnings.

## "Warnings about frontmatter"
- Open the note named in warning output.
- Ensure note starts with `---` frontmatter block.
- Fix required keys (`id`, `created_at`, etc.).

## "Emotion was skipped"
- Use only supported emotion names.
- Ensure each score is an integer 0-10.

## "Arousal output seems wrong"
- Check `--arousal on` is set.
- Confirm `Adult/` note has `enabled: true`.
- Ensure intimate tags/emotions are present in relevant memories.

## "Too much text in compiled file"
- Use limits:
```powershell
python compile_context.py --vault "C:\Path\To\Vault" --max-memories 80 --max-chars 120000
```

## "Continuity feels weak"
- Add more specific memories.
- Increase importance for key events.
- Add tags and emotions consistently.
- Use soul crystallizations for permanent anchors.
