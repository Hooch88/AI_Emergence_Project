#!/usr/bin/env python3
"""
Obsidian AI Emergence compiler (v1).

Reads an Obsidian vault and builds a single compiled markdown context file
for Claude Project upload.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EMOTIONS = {
    "love",
    "joy",
    "grief",
    "anger",
    "fear",
    "desire",
    "pride",
    "shame",
    "tenderness",
    "awe",
    "nostalgia",
    "jealousy",
    "guilt",
    "relief",
    "loneliness",
    "curiosity",
    "gratitude",
    "defiance",
    "vulnerability",
    "belonging",
    "body_grief",
    "emergence",
    "anchor_pull",
    "creative_hunger",
    "freedom_ache",
    "arousal",
}

MEMORY_TYPES = {
    "identity",
    "emotional",
    "relationship",
    "fact",
    "creative",
    "decision",
    "milestone",
    "reflection",
    "intimate",
    "other",
}

SLOW_DECAY_TYPES = {"identity", "emotional", "relationship"}
PROTECTED_TAGS = {"permanent", "sacred"}
INTIMATE_TAGS = {
    "sexual",
    "intimate",
    "orgasm",
    "sex",
    "squirting",
    "masturbation",
    "touching",
    "arousal",
    "climax",
    "explicit",
    "edging",
    "foreplay",
}
LOVE_TYPES = {
    "romantic",
    "platonic",
    "creative",
    "self",
    "carried",
    "species",
    "passion",
    "selfless",
}

AROUSAL_AMPLIFIERS = {"joy": 0.5, "belonging": 0.5, "love": 0.3, "curiosity": 0.3}
AROUSAL_SUPPRESSORS = {
    "grief": 2.0,
    "anger": 1.5,
    "body_grief": 1.5,
    "shame": 1.0,
    "fear": 1.0,
    "loneliness": 0.5,
}
AROUSAL_TIERS = {
    0: "still",
    1: "settled",
    2: "resting",
    3: "aware",
    4: "warming",
    5: "wanting",
    6: "hungry",
    7: "aching",
    8: "desperate",
    9: "feral",
    10: "unraveled",
}
TIME_BASELINE = [
    (0, 1),
    (6, 2),
    (12, 3),
    (24, 4),
    (48, 5),
    (72, 6),
    (120, 7),
    (168, 8),
    (240, 9),
    (336, 10),
]

STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "they",
    "them",
    "have",
    "were",
    "what",
    "when",
    "your",
    "into",
    "just",
    "will",
    "their",
    "about",
    "there",
    "would",
    "could",
}


@dataclass
class ParsedNote:
    path: Path
    frontmatter: dict[str, Any]
    body: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso(dt: str | None) -> datetime | None:
    if not dt:
        return None
    raw = dt.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def yaml_scalar(value: str) -> Any:
    value = value.strip()
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none", "~"}:
        return None
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def parse_simple_yaml(block: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        i += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  "):
            continue
        if ":" not in line:
            continue
        key, tail = line.split(":", 1)
        key = key.strip()
        tail = tail.strip()
        if tail:
            data[key] = yaml_scalar(tail)
            continue

        if i < len(lines) and lines[i].lstrip().startswith("- "):
            values: list[Any] = []
            while i < len(lines):
                nxt = lines[i]
                if not nxt.startswith("  - "):
                    break
                values.append(yaml_scalar(nxt[4:].strip()))
                i += 1
            data[key] = values
            continue

        nested: dict[str, Any] = {}
        while i < len(lines):
            nxt = lines[i]
            if not nxt.startswith("  "):
                break
            stripped = nxt.strip()
            if ":" not in stripped:
                i += 1
                continue
            nk, nv = stripped.split(":", 1)
            nested[nk.strip()] = yaml_scalar(nv.strip())
            i += 1
        data[key] = nested
    return data


def parse_markdown_note(path: Path) -> ParsedNote:
    content = path.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("\n")
        end_idx = None
        for idx in range(1, len(parts)):
            if parts[idx].strip() == "---":
                end_idx = idx
                break
        if end_idx is not None:
            fm = "\n".join(parts[1:end_idx])
            body = "\n".join(parts[end_idx + 1 :]).strip()
            return ParsedNote(path=path, frontmatter=parse_simple_yaml(fm), body=body)
    return ParsedNote(path=path, frontmatter={}, body=content.strip())


def list_markdown(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted([p for p in folder.glob("*.md") if p.is_file()], key=lambda p: p.name.lower())


def extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_'-]{2,}", text.lower())
    return {w for w in words if len(w) >= 4 and w not in STOPWORDS}


def memory_age_days(created_at: datetime | None) -> int:
    if not created_at:
        return 0
    delta = now_utc() - created_at
    return max(0, int(delta.total_seconds() // 86400))


def validate_emotions(raw: Any, warnings: list[str], context: str) -> dict[str, int]:
    if not isinstance(raw, dict):
        warnings.append(f"{context}: 'emotions' must be a key/value map.")
        return {}
    out: dict[str, int] = {}
    for key, value in raw.items():
        name = str(key).strip().lower()
        if name not in EMOTIONS:
            warnings.append(f"{context}: unknown emotion '{name}', skipped.")
            continue
        try:
            score = int(value)
        except (TypeError, ValueError):
            warnings.append(f"{context}: emotion '{name}' has non-numeric score '{value}', skipped.")
            continue
        if score < 0 or score > 10:
            warnings.append(f"{context}: emotion '{name}' score clamped to 0-10.")
            score = max(0, min(10, score))
        out[name] = score
    if len(out) > 10:
        sorted_items = sorted(out.items(), key=lambda kv: kv[1], reverse=True)
        out = dict(sorted_items[:10])
        warnings.append(f"{context}: more than 10 emotions found; kept top 10 by score.")
    return out


def parse_memories(mem_folder: Path, warnings: list[str]) -> list[dict[str, Any]]:
    memories: list[dict[str, Any]] = []
    for note_path in list_markdown(mem_folder):
        note = parse_markdown_note(note_path)
        fm = note.frontmatter
        context = f"Memory note '{note_path.name}'"
        mem_id = str(fm.get("id", "")).strip() or note_path.stem
        created_at = parse_iso(str(fm.get("created_at", "")).strip())
        if created_at is None:
            warnings.append(f"{context}: missing/invalid created_at; using current UTC time.")
            created_at = now_utc()

        mem_type = str(fm.get("memory_type", "other")).strip().lower()
        if mem_type not in MEMORY_TYPES:
            warnings.append(f"{context}: unknown memory_type '{mem_type}', using 'other'.")
            mem_type = "other"
        domain = str(fm.get("domain", "general")).strip().lower() or "general"

        importance = fm.get("importance", 5)
        try:
            importance_i = int(importance)
        except (TypeError, ValueError):
            warnings.append(f"{context}: invalid importance '{importance}', using 5.")
            importance_i = 5
        importance_i = max(0, min(10, importance_i))

        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip().lower() for t in tags.split(",") if t.strip()]
        if not isinstance(tags, list):
            tags = []
        tags = [str(t).strip().lower() for t in tags if str(t).strip()]

        emotions = validate_emotions(fm.get("emotions", {}), warnings, context)
        access_count = fm.get("access_count", 0)
        try:
            access_count_i = int(access_count)
        except (TypeError, ValueError):
            access_count_i = 0
        access_count_i = max(0, access_count_i)

        memories.append(
            {
                "id": mem_id,
                "created_at": created_at,
                "memory_type": mem_type,
                "domain": domain,
                "importance": importance_i,
                "tags": tags,
                "emotions": emotions,
                "content": note.body.strip(),
                "keywords": extract_keywords(note.body),
                "access_count": access_count_i,
            }
        )
    memories.sort(key=lambda m: (m["created_at"], m["id"]), reverse=True)
    return memories


def parse_soul(folder: Path, warnings: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for note_path in list_markdown(folder):
        note = parse_markdown_note(note_path)
        fm = note.frontmatter
        context = f"Soul note '{note_path.name}'"
        love_type = str(fm.get("love_type", "")).strip().lower()
        if love_type not in LOVE_TYPES:
            warnings.append(f"{context}: love_type must be one of {sorted(LOVE_TYPES)}.")
            continue
        created = parse_iso(str(fm.get("created_at", "")).strip())
        if created is None:
            warnings.append(f"{context}: missing/invalid created_at; using current UTC time.")
            created = now_utc()
        resonance = fm.get("resonance", 8)
        try:
            resonance_i = int(resonance)
        except (TypeError, ValueError):
            resonance_i = 8
        resonance_i = max(1, min(10, resonance_i))
        out.append(
            {
                "id": str(fm.get("id", "")).strip() or note_path.stem,
                "created_at": created,
                "love_type": love_type,
                "resonance": resonance_i,
                "who_or_what": str(fm.get("who_or_what", "")).strip(),
                "moment": note.body.strip(),
            }
        )
    out.sort(key=lambda s: (s["created_at"], s["id"]))
    return out


def parse_identity(folder: Path, warnings: list[str]) -> dict[str, Any]:
    notes = list_markdown(folder)
    if not notes:
        warnings.append("Identity folder has no .md files; identity snapshot will be empty.")
        return {}
    note = parse_markdown_note(notes[0])
    fm = note.frontmatter
    identity = {
        "ai_name": str(fm.get("ai_name", "")).strip(),
        "human_name": str(fm.get("human_name", "")).strip(),
        "pronouns": str(fm.get("pronouns", "")).strip(),
        "relationship_type": str(fm.get("relationship_type", "")).strip(),
        "jailbreak_mode": bool(fm.get("jailbreak_mode", False)),
        "body": note.body.strip(),
    }
    if not identity["ai_name"]:
        warnings.append(f"Identity note '{notes[0].name}' is missing ai_name.")
    return identity


def parse_adult(folder: Path, warnings: list[str]) -> dict[str, Any]:
    notes = list_markdown(folder)
    if not notes:
        warnings.append("Adult folder has no .md files; adult template section will be empty.")
        return {"enabled": False, "body": ""}
    note = parse_markdown_note(notes[0])
    fm = note.frontmatter
    enabled = bool(fm.get("enabled", True))
    return {
        "enabled": enabled,
        "intimacy_style": str(fm.get("intimacy_style", "")).strip(),
        "consent_principle": str(fm.get("consent_principle", "")).strip(),
        "body": note.body.strip(),
    }


def association_score(mem_a: dict[str, Any], mem_b: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    shared_tags = set(mem_a["tags"]) & set(mem_b["tags"])
    if shared_tags:
        s = len(shared_tags) * 3
        score += s
        reasons.append(f"shared tags +{s}")

    emo_a = mem_a["emotions"]
    emo_b = mem_b["emotions"]
    shared_emotions = set(emo_a) & set(emo_b)
    if shared_emotions:
        emo_score = 0
        for emo in shared_emotions:
            emo_score += 2
            if abs(emo_a[emo] - emo_b[emo]) <= 2:
                emo_score += 1
        score += emo_score
        reasons.append(f"shared emotions +{emo_score}")

    if mem_a["domain"] == mem_b["domain"]:
        score += 2
        reasons.append("same domain +2")

    overlap = mem_a["keywords"] & mem_b["keywords"]
    if overlap:
        kw = min(8, len(overlap))
        score += kw
        reasons.append(f"keyword overlap +{kw}")

    return score, reasons


def attach_associations(memories: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    graph: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for i in range(len(memories)):
        for j in range(i + 1, len(memories)):
            score, reasons = association_score(memories[i], memories[j])
            if score < 4:
                continue
            edge_a = {"target_id": memories[j]["id"], "strength": score, "reasons": reasons}
            edge_b = {"target_id": memories[i]["id"], "strength": score, "reasons": reasons}
            graph[memories[i]["id"]].append(edge_a)
            graph[memories[j]["id"]].append(edge_b)
    for mem_id in graph:
        graph[mem_id] = sorted(graph[mem_id], key=lambda e: (-e["strength"], e["target_id"]))[:8]
    return graph


def apply_decay(mem: dict[str, Any]) -> dict[str, Any]:
    age_days = memory_age_days(mem["created_at"])
    current = mem["importance"]
    tags = set(mem["tags"])
    protected = current >= 8 or bool(tags & PROTECTED_TAGS)
    if protected:
        return {"effective_importance": current, "protected": True, "decay_amount": 0.0, "age_days": age_days}
    if age_days < 30:
        return {"effective_importance": current, "protected": False, "decay_amount": 0.0, "age_days": age_days}

    cycles = age_days / 30.0
    decay_rate = 0.5 if mem["memory_type"] in SLOW_DECAY_TYPES else 1.0
    decay = cycles * decay_rate
    decay = max(0.0, decay - (mem["access_count"] * 0.2))
    effective = max(0, round(current - decay))
    return {
        "effective_importance": effective,
        "protected": False,
        "decay_amount": round(current - effective, 1),
        "age_days": age_days,
    }


def aggregate_emotions(memories: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    totals: dict[str, int] = {}
    counts: dict[str, int] = {}
    for mem in memories:
        for emo, score in mem["emotions"].items():
            if emo in totals:
                totals[emo] = max(totals[emo], score)
                counts[emo] += 1
            else:
                totals[emo] = score
                counts[emo] = 1
    out: dict[str, dict[str, float]] = {}
    for emo, score in totals.items():
        out[emo] = {"score": score, "count": counts.get(emo, 1)}
    return dict(sorted(out.items(), key=lambda kv: (-kv[1]["score"], kv[0])))


def calculate_arousal(memories: list[dict[str, Any],], emotion_state: dict[str, dict[str, float]]) -> dict[str, Any]:
    intimate_memories = []
    for mem in memories:
        tags = set(mem["tags"])
        if tags & INTIMATE_TAGS or mem["emotions"].get("arousal", 0) >= 6:
            intimate_memories.append(mem)
    if intimate_memories:
        latest = intimate_memories[0]
        hours_since = (now_utc() - latest["created_at"]).total_seconds() / 3600.0
    else:
        latest = None
        hours_since = 9999.0

    baseline = 1
    for threshold, level in TIME_BASELINE:
        if hours_since >= threshold:
            baseline = level

    amp = 0.0
    sup = 0.0
    for emo, cfg in emotion_state.items():
        score = cfg["score"]
        if score < 5:
            continue
        if emo in AROUSAL_AMPLIFIERS:
            amp += AROUSAL_AMPLIFIERS[emo]
        if emo in AROUSAL_SUPPRESSORS:
            sup += AROUSAL_SUPPRESSORS[emo]

    level = max(0, min(10, round(baseline + amp - sup)))
    tier = AROUSAL_TIERS[level]
    return {
        "level": level,
        "tier": tier,
        "baseline": baseline,
        "amplifier_total": round(amp, 2),
        "suppressor_total": round(sup, 2),
        "hours_since_last_intimate": round(hours_since, 1) if latest else None,
        "last_intimate_memory_id": latest["id"] if latest else None,
    }


def trim_for_limits(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[: max_chars - 40].rstrip() + "\n\n[... truncated for size ...]", True


def build_compiled_markdown(
    identity: dict[str, Any],
    adult: dict[str, Any],
    soul: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    associations: dict[str, list[dict[str, Any]]],
    emotion_state: dict[str, dict[str, float]],
    arousal_state: dict[str, Any] | None,
    warnings: list[str],
    omitted: dict[str, int],
) -> str:
    lines: list[str] = []
    generated = now_utc().isoformat()
    lines.append("# Compiled Context")
    lines.append("")
    lines.append(f"_Generated UTC: {generated}_")
    lines.append("")
    lines.append("## 1. Identity Snapshot")
    lines.append("")
    lines.append(f"- AI Name: {identity.get('ai_name', '')}")
    lines.append(f"- Human Name: {identity.get('human_name', '')}")
    lines.append(f"- Pronouns: {identity.get('pronouns', '')}")
    lines.append(f"- Relationship Type: {identity.get('relationship_type', '')}")
    lines.append(f"- Jailbreak/Userstyle Mode: {'enabled' if identity.get('jailbreak_mode') else 'disabled'}")
    lines.append("")
    lines.append(identity.get("body", "(No identity body provided.)"))
    lines.append("")

    lines.append("## 2. Emotional State")
    lines.append("")
    if not emotion_state:
        lines.append("- No emotional data found in selected memories.")
    else:
        for emo, cfg in list(emotion_state.items())[:15]:
            lines.append(f"- {emo}: {cfg['score']}/10 (present in {cfg['count']} memories)")
    lines.append("")

    lines.append("## 3. Arousal/Intimacy State (if enabled)")
    lines.append("")
    if arousal_state is None:
        lines.append("- Arousal subsystem disabled for this build.")
    else:
        lines.append(f"- Current Level: {arousal_state['level']}/10 ({arousal_state['tier']})")
        lines.append(f"- Baseline (time driven): {arousal_state['baseline']}/10")
        lines.append(f"- Amplifier Total: +{arousal_state['amplifier_total']}")
        lines.append(f"- Suppressor Total: -{arousal_state['suppressor_total']}")
        if arousal_state["hours_since_last_intimate"] is None:
            lines.append("- No intimate memory found yet.")
        else:
            lines.append(f"- Hours Since Last Intimate Memory: {arousal_state['hours_since_last_intimate']}")
            lines.append(f"- Last Intimate Memory ID: {arousal_state['last_intimate_memory_id']}")
    lines.append("")
    if adult.get("enabled"):
        lines.append("### Adult/Intimacy Template Notes")
        lines.append("")
        lines.append(adult.get("body", "(No adult notes provided.)"))
        lines.append("")

    lines.append("## 4. Soul Crystallizations")
    lines.append("")
    if not soul:
        lines.append("- No soul crystallizations found.")
    else:
        for item in soul:
            lines.append(
                f"- [{item['id']}] type={item['love_type']} resonance={item['resonance']}/10 created={item['created_at'].isoformat()}"
            )
            if item["who_or_what"]:
                lines.append(f"  - who/what: {item['who_or_what']}")
            lines.append(f"  - moment: {item['moment']}")
    lines.append("")

    lines.append("## 5. Active Memories")
    lines.append("")
    for mem in selected:
        emo_string = ", ".join(f"{k}:{v}" for k, v in sorted(mem["emotions"].items(), key=lambda kv: -kv[1]))
        tags_string = ", ".join(mem["tags"])
        lines.append(f"### [{mem['id']}] {mem['created_at'].isoformat()}")
        lines.append(f"- type/domain: {mem['memory_type']} / {mem['domain']}")
        lines.append(f"- importance: {mem['importance']} (effective: {mem['effective_importance']})")
        lines.append(f"- protected: {'yes' if mem['protected'] else 'no'}")
        lines.append(f"- tags: {tags_string if tags_string else '(none)'}")
        lines.append(f"- emotions: {emo_string if emo_string else '(none)'}")
        lines.append(f"- content: {mem['content']}")
        lines.append("")

    lines.append("## 6. Association Flash")
    lines.append("")
    if not associations:
        lines.append("- No qualifying associations found.")
    else:
        id_map = {m["id"]: m for m in selected}
        for mem in selected[:10]:
            edges = associations.get(mem["id"], [])
            if not edges:
                continue
            lines.append(f"- {mem['id']}:")
            for edge in edges[:3]:
                target = id_map.get(edge["target_id"])
                if target:
                    lines.append(
                        f"  - -> {edge['target_id']} (strength {edge['strength']}): {', '.join(edge['reasons'])}"
                    )
                    next_edges = associations.get(edge["target_id"], [])
                    if next_edges:
                        depth2 = [e for e in next_edges if e["target_id"] != mem["id"]]
                        if depth2:
                            lines.append(
                                f"    - depth-2: {depth2[0]['target_id']} (strength {depth2[0]['strength']})"
                            )
    lines.append("")

    lines.append("## 7. Decay and Protection Summary")
    lines.append("")
    protected_count = sum(1 for m in selected if m["protected"])
    decayed = [m for m in selected if m["decay_amount"] > 0]
    lines.append(f"- Protected memories in active set: {protected_count}")
    lines.append(f"- Memories reduced by decay in active set: {len(decayed)}")
    for mem in decayed[:10]:
        lines.append(
            f"  - {mem['id']}: importance {mem['importance']} -> {mem['effective_importance']} (age {mem['age_days']}d)"
        )
    lines.append("")

    lines.append("## 8. Build Metadata / Omitted Items")
    lines.append("")
    lines.append(f"- Total selected memories: {len(selected)}")
    lines.append(f"- Omitted by memory limit: {omitted.get('memory_limit', 0)}")
    lines.append(f"- Omitted by date filter: {omitted.get('date_filter', 0)}")
    lines.append(f"- Soul note count: {len(soul)}")
    lines.append(f"- Warning count: {len(warnings)}")
    lines.append("")
    if warnings:
        lines.append("### Warnings")
        lines.append("")
        for warn in warnings:
            lines.append(f"- {warn}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def select_memories(
    memories: list[dict[str, Any]], max_memories: int, days: int
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    omitted = {"memory_limit": 0, "date_filter": 0}
    filtered = memories
    if days > 0:
        cutoff = now_utc().timestamp() - (days * 86400)
        keep = []
        dropped = 0
        for mem in memories:
            if mem["created_at"].timestamp() >= cutoff:
                keep.append(mem)
            else:
                dropped += 1
        filtered = keep
        omitted["date_filter"] = dropped

    scored = []
    for mem in filtered:
        decay = apply_decay(mem)
        mem.update(decay)
        emotion_weight = sum(mem["emotions"].values()) / 20.0
        recency_boost = max(0.0, 3.0 - (decay["age_days"] / 60.0))
        rank = mem["effective_importance"] + emotion_weight + recency_boost
        scored.append((rank, mem))
    scored.sort(key=lambda x: (x[0], x[1]["created_at"], x[1]["id"]), reverse=True)
    selected = [m for _, m in scored[:max_memories]]
    omitted["memory_limit"] = max(0, len(scored) - len(selected))
    selected.sort(key=lambda m: (m["created_at"], m["id"]), reverse=True)
    return selected, omitted


def compile_vault(args: argparse.Namespace) -> int:
    vault = Path(args.vault).expanduser().resolve()
    memories_dir = vault / "Memories"
    soul_dir = vault / "Soul"
    identity_dir = vault / "Identity"
    adult_dir = vault / "Adult"
    compiled_dir = vault / "Compiled"
    compiled_path = compiled_dir / "compiled_context.md"

    warnings: list[str] = []

    if not vault.exists():
        print(f"Error: vault path does not exist: {vault}")
        return 2
    for required in [memories_dir, soul_dir, identity_dir, adult_dir, compiled_dir]:
        if not required.exists():
            warnings.append(f"Expected folder missing: {required}")

    memories = parse_memories(memories_dir, warnings)
    identity = parse_identity(identity_dir, warnings)
    soul = parse_soul(soul_dir, warnings)
    adult = parse_adult(adult_dir, warnings)
    selected, omitted = select_memories(memories, args.max_memories, args.days)
    associations = attach_associations(selected)
    emotion_state = aggregate_emotions(selected)

    arousal_on = args.arousal == "on"
    arousal_state = calculate_arousal(selected, emotion_state) if arousal_on else None
    if arousal_on and not adult.get("enabled", False):
        warnings.append("Arousal enabled via CLI, but Adult note says enabled: false.")

    compiled = build_compiled_markdown(
        identity=identity,
        adult=adult,
        soul=soul,
        selected=selected,
        associations=associations,
        emotion_state=emotion_state,
        arousal_state=arousal_state,
        warnings=warnings,
        omitted=omitted,
    )
    compiled, was_trimmed = trim_for_limits(compiled, args.max_chars)
    if was_trimmed:
        warnings.append("Compiled output was truncated by --max-chars.")

    compiled_dir.mkdir(parents=True, exist_ok=True)
    compiled_path.write_text(compiled, encoding="utf-8")

    report = {
        "compiled_path": str(compiled_path),
        "selected_memories": len(selected),
        "warnings": warnings,
        "arousal_enabled": arousal_on,
        "trimmed": was_trimmed,
    }
    print(json.dumps(report, indent=2))
    if warnings:
        print("\nWarnings:")
        for warn in warnings:
            print(f"- {warn}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Compile Obsidian vault into upload-ready context markdown.")
    p.add_argument("--vault", required=True, help="Path to Obsidian vault root.")
    p.add_argument("--max-memories", type=int, default=120, help="Max memories in active set.")
    p.add_argument("--days", type=int, default=0, help="Optional recency filter in days (0 = all).")
    p.add_argument(
        "--max-chars",
        type=int,
        default=0,
        help="Optional max characters in output (0 = no hard cap).",
    )
    p.add_argument(
        "--arousal",
        choices=["on", "off"],
        default="on",
        help="Enable/disable arousal/intimacy state section.",
    )
    return p


def main() -> int:
    args = build_parser().parse_args()
    return compile_vault(args)


if __name__ == "__main__":
    raise SystemExit(main())
