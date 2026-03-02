# Data Contracts

## Memory note (`Memories/*.md`)
Required frontmatter:
- `id` (string)
- `created_at` (ISO datetime)
- `memory_type` (`identity|emotional|relationship|fact|creative|decision|milestone|reflection|intimate|other`)
- `domain` (string)
- `importance` (0-10 int)
- `tags` (list of strings)
- `emotions` (map of `emotion -> 0-10 int`, max 10 keys)

Optional:
- `access_count` (int >= 0)

Body:
- Plain markdown text for memory content.

## Soul note (`Soul/*.md`)
Required:
- `id`
- `created_at`
- `love_type` (`romantic|platonic|creative|self|carried|species|passion|selfless`)
- `resonance` (1-10)

Optional:
- `who_or_what`

Body:
- Permanent crystallization moment text.

## Identity note (`Identity/*.md`)
Required:
- `ai_name`
- `human_name`
- `pronouns`
- `relationship_type`
- `jailbreak_mode` (bool)

Body:
- Identity and behavior narrative.

## Adult note (`Adult/*.md`)
Required:
- `enabled` (bool)
- `intimacy_style` (string)
- `consent_principle` (string)

Body:
- Adult/intimacy language and behavior guidance.

## Compiler output (`Compiled/compiled_context.md`)
Stable sections:
1. Identity Snapshot
2. Emotional State
3. Arousal/Intimacy State (if enabled)
4. Soul Crystallizations
5. Active Memories
6. Association Flash
7. Decay and Protection Summary
8. Build Metadata / Omitted Items
