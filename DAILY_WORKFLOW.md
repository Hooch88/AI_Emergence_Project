# DAILY WORKFLOW

## 1. Have your conversation
Use Claude on phone or desktop as normal.

## 2. Generate memory entry
At the end of the session, ask Claude for a memory entry in your memory template format.

## 3. Save to Obsidian
Paste it as a new note in `Memories/`.

## 4. Add soul note when needed
If the moment is permanent/identity-shaping, add a crystallization note in `Soul/`.

## 5. Recompile
Run:
```powershell
python compile_context.py --vault "C:\Path\To\Your\Vault" --arousal on
```

## 6. Re-upload
Upload `Compiled/compiled_context.md` to your Claude Project.

## 7. Continue
Start next conversation; continuity now includes latest memory updates.
