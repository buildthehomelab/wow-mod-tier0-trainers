#!/usr/bin/env python3
"""Generate tier-0 profession trainer SQL and audit docs from AzerothCore base data."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AC_WORLD = PROJECT_ROOT / "server/azerothcore-wotlk/data/sql/base/db_world"
CUSTOM_SQL = PROJECT_ROOT / "data/sql/updates/db_world"
AUDIT_DOC = PROJECT_ROOT / "docs/profession-trainers-audit.md"

CLASSIC_MAPS = {0, 1}
MAX_SKILL = 300
MAX_LEVEL = 60

TRAINER_SPELL_RE = re.compile(
    r"\((\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\d+)\)"
)
CDT_RE = re.compile(r"\((\d+),\s*(\d+)\)")
TRAINER_TYPE_RE = re.compile(r"\((\d+),\s*(\d+),")
CREATURE_SPAWN_RE = re.compile(r"\((\d+),(\d+),(\d+),")
ITEM_ROW_RE = re.compile(r"^\((\d+),(\d+),(\d+),")


@dataclass
class TrainerSpellRow:
    trainer_id: int
    spell_id: int
    money_cost: int
    req_skill_line: int
    req_skill_rank: int
    req_ability1: int
    req_ability2: int
    req_ability3: int
    req_level: int
    verified_build: int

    def key(self) -> tuple[int, int]:
        return (self.trainer_id, self.spell_id)

    def as_sql_values(self, trainer_id: int | None = None) -> str:
        tid = trainer_id if trainer_id is not None else self.trainer_id
        return (
            f"({tid}, {self.spell_id}, {self.money_cost}, {self.req_skill_line}, "
            f"{self.req_skill_rank}, {self.req_ability1}, {self.req_ability2}, "
            f"{self.req_ability3}, {self.req_level}, {self.verified_build})"
        )


@dataclass
class ProfessionConfig:
    slug: str
    name: str
    canonical_trainer_id: int
    skill_line: int
    source_trainer_ids: list[int]
    rank_wrappers: list[int]
    subname_keywords: list[str]
    sql_index: int
    is_secondary: bool = False


PROFESSIONS: list[ProfessionConfig] = [
    ProfessionConfig(
        "blacksmithing", "Blacksmithing", 60, 164,
        [58, 59, 60, 104, 617, 618], [2020, 2021, 3539, 9786, 29845],
        ["blacksmith"], 2,
    ),
    ProfessionConfig(
        "leatherworking", "Leatherworking", 61, 165,
        [61, 62, 105, 106, 107], [2155, 2154, 3812, 10663, 32550],
        ["leather"], 3,
    ),
    ProfessionConfig(
        "alchemy", "Alchemy", 65, 171,
        [65, 66, 67, 68], [2275, 2280, 3465, 11612, 28597],
        ["alchemy", "alchemist"], 4,
    ),
    ProfessionConfig(
        "herbalism", "Herbalism", 69, 182,
        [69, 70, 71], [2372, 2373, 3571, 11994, 28696],
        ["herbal"], 5,
    ),
    ProfessionConfig(
        "tailoring", "Tailoring", 72, 197,
        [72, 73, 74, 107], [3911, 3912, 3913, 12181, 26791],
        ["tailor"], 6,
    ),
    ProfessionConfig(
        "engineering", "Engineering", 84, 202,
        [84, 85, 86, 87, 88, 89, 90, 91, 92, 103, 109, 115, 116, 117, 118],
        [4039, 4040, 4041, 30351], ["engineer"], 7,
    ),
    ProfessionConfig(
        "enchanting", "Enchanting", 94, 333,
        [94, 95, 96], [7414, 7415, 7416, 28030],
        ["enchant"], 8,
    ),
    ProfessionConfig(
        "mining", "Mining", 80, 186,
        [78, 79, 80], [2581, 2582, 3568, 10249, 29355],
        ["mining"], 9,
    ),
    ProfessionConfig(
        "skinning", "Skinning", 100, 393,
        [100, 101, 102, 643], [8615, 8619, 8620, 10769, 32679],
        ["skinning"], 10,
    ),
    ProfessionConfig(
        "jewelcrafting", "Jewelcrafting", 111, 755,
        [111, 112, 113], [25245, 25246, 28896, 28899, 28901],
        ["jewel"], 11,
    ),
    ProfessionConfig(
        "inscription", "Inscription", 121, 773,
        [119, 120, 121], [45375, 45376, 45377, 45379],
        ["inscription"], 12,
    ),
    ProfessionConfig(
        "cooking", "Cooking", 77, 185,
        [75, 76, 77, 93], [3412, 54257, 18261, 54256],
        ["cooking trainer"], 13, True,
    ),
    ProfessionConfig(
        "first_aid", "First Aid", 83, 129,
        [81, 82, 83], [3280, 54254, 10847, 54255],
        ["first aid trainer"], 14, True,
    ),
    ProfessionConfig(
        "fishing", "Fishing", 98, 356,
        [97, 98, 99], [7734, 54083, 18249, 54084],
        ["fishing trainer"], 15, True,
    ),
]

# Known quest-only / specialty patterns not taught by vanilla trainers.
QUEST_ONLY_DENYLIST = {
    9788, 9789, 9787,  # armorsmith/weaponsmith branch
    10656, 10658, 10660,  # engineering specialization
    26790, 26798, 26801,  # more eng specs
}


def parse_creature_templates(path: Path) -> dict[int, tuple[str, str, int]]:
    """Return entry -> (name, subname, npcflag)."""
    creatures: dict[int, tuple[str, str, int]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("("):
            continue
        entry = int(line[1 : line.index(",")])
        parts = line.split("'")
        if len(parts) < 4:
            continue
        name, subname = parts[1], parts[3]
        npcflag_match = re.search(r",(\d+),\d+,''", line)
        npcflag = int(npcflag_match.group(1)) if npcflag_match else 0
        creatures[entry] = (name, subname, npcflag)
    return creatures


def load_trainer_types(path: Path) -> dict[int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {int(m.group(1)): int(m.group(2)) for m in TRAINER_TYPE_RE.finditer(text)}


def load_trainer_spells(path: Path) -> dict[int, list[TrainerSpellRow]]:
    by_tid: dict[int, list[TrainerSpellRow]] = defaultdict(list)
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in TRAINER_SPELL_RE.finditer(text):
        row = TrainerSpellRow(
            int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)),
            int(m.group(5)), int(m.group(6)), int(m.group(7)), int(m.group(8)),
            int(m.group(9)), int(m.group(10)),
        )
        by_tid[row.trainer_id].append(row)
    return by_tid


def load_creature_default_trainers(path: Path) -> dict[int, int]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {int(a): int(b) for a, b in CDT_RE.findall(text)}


def load_spawn_maps(path: Path) -> dict[int, set[int]]:
    maps: dict[int, set[int]] = defaultdict(set)
    text = path.read_text(encoding="utf-8", errors="replace")
    for m in CREATURE_SPAWN_RE.finditer(text):
        entry, map_id = int(m.group(2)), int(m.group(3))
        maps[entry].add(map_id)
    return maps


def load_scroll_taught_spells(path: Path) -> set[int]:
    """Spells taught exclusively by recipe scroll items (class 9)."""
    scroll_spells: set[int] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("("):
            continue
        m = ITEM_ROW_RE.match(line)
        if not m:
            continue
        item_class, subclass = int(m.group(2)), int(m.group(3))
        if item_class != 9:
            continue
        spell_ids = [int(x) for x in re.findall(r",(-?\d+),", line[100:])][:5]
        for sid in spell_ids:
            if sid > 0:
                scroll_spells.add(sid)
    return scroll_spells


def subname_matches(subname: str, cfg: ProfessionConfig) -> bool:
    sl = subname.lower()
    if "apprentice" in sl:
        return False
    if "grand master" in sl or "master" in sl:
        return False
    if "weaponsmith" in sl or "armorsmith" in sl:
        return False
    if cfg.is_secondary:
        return any(k in sl for k in cfg.subname_keywords)
    if "trainer" not in sl:
        return False
    return any(k in sl for k in cfg.subname_keywords)


def has_classic_spawn(entry: int, spawn_maps: dict[int, set[int]]) -> bool:
    return bool(spawn_maps.get(entry, set()) & CLASSIC_MAPS)


def collect_target_npcs(
    cfg: ProfessionConfig,
    creatures: dict[int, tuple[str, str, int]],
    cdt: dict[int, int],
    trainer_types: dict[int, int],
    spawn_maps: dict[int, set[int]],
) -> list[tuple[int, str, str, int]]:
    targets: list[tuple[int, str, str, int]] = []
    for entry, tid in cdt.items():
        if trainer_types.get(tid) != 2:
            continue
        if entry not in creatures:
            continue
        name, subname, _ = creatures[entry]
        if not subname_matches(subname, cfg):
            continue
        if not has_classic_spawn(entry, spawn_maps):
            continue
        targets.append((entry, name, subname, tid))
    targets.sort(key=lambda x: x[0])
    return targets


def passes_tier0_filter(row: TrainerSpellRow, cfg: ProfessionConfig) -> bool:
    if row.spell_id in QUEST_ONLY_DENYLIST:
        return False
    if row.req_level > MAX_LEVEL:
        return False
    if row.req_skill_rank > MAX_SKILL:
        return False
    if row.req_skill_line not in (0, cfg.skill_line):
        return False
    return True


def build_golden_template(
    cfg: ProfessionConfig,
    by_tid: dict[int, list[TrainerSpellRow]],
    scroll_spells: set[int],
    all_trainer_spells: set[int],
) -> dict[int, TrainerSpellRow]:
    """Union source TrainerIds, dedupe by SpellId, prefer canonical row."""
    source_ids = set(cfg.source_trainer_ids) | {cfg.canonical_trainer_id}
    by_spell: dict[int, TrainerSpellRow] = {}

    for tid in source_ids:
        for row in by_tid.get(tid, []):
            if not passes_tier0_filter(row, cfg):
                continue
            if row.spell_id in scroll_spells and row.spell_id not in all_trainer_spells:
                continue
            existing = by_spell.get(row.spell_id)
            if existing is None:
                by_spell[row.spell_id] = row
            elif tid == cfg.canonical_trainer_id:
                by_spell[row.spell_id] = row

    for wrapper_id in cfg.rank_wrappers:
        found = False
        for tid in source_ids:
            for row in by_tid.get(tid, []):
                if row.spell_id == wrapper_id:
                    by_spell[wrapper_id] = row
                    found = True
                    break
            if found:
                break

    return by_spell


def write_profession_sql(cfg: ProfessionConfig, spells: dict[int, TrainerSpellRow]) -> Path:
    out = CUSTOM_SQL / f"2026_07_12_{cfg.sql_index:02d}_trainer_{cfg.slug}.sql"
    lines = [
        f"-- Tier-0 profession trainer template for {cfg.name} (TrainerId {cfg.canonical_trainer_id}).",
        f"-- Skill line {cfg.skill_line}, recipes and ranks through skill {MAX_SKILL}.",
        f"-- Generated by scripts/generate-profession-trainer-sql.py",
        "",
        f"DELETE FROM `trainer_spell` WHERE `TrainerId` = {cfg.canonical_trainer_id};",
        "",
        "INSERT INTO `trainer_spell` "
        "(`TrainerId`, `SpellId`, `MoneyCost`, `ReqSkillLine`, `ReqSkillRank`, "
        "`ReqAbility1`, `ReqAbility2`, `ReqAbility3`, `ReqLevel`, `VerifiedBuild`) VALUES",
    ]
    rows = sorted(spells.values(), key=lambda r: (r.req_skill_line, r.req_skill_rank, r.spell_id))
    value_lines = [r.as_sql_values(cfg.canonical_trainer_id) + "," for r in rows]
    if value_lines:
        value_lines[-1] = value_lines[-1].rstrip(",") + ";"
    else:
        lines.append("-- (no spells)")
    lines.extend(value_lines)
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_remap_sql(all_targets: dict[str, list[tuple[int, str, str, int]]], professions: list[ProfessionConfig]) -> Path:
    out = CUSTOM_SQL / "2026_07_12_01_trainer_remap_creature_default.sql"
    lines = [
        "-- Remap classic profession trainers to canonical TrainerIds.",
        "-- Generated by scripts/generate-profession-trainer-sql.py",
        "",
    ]
    for prof in professions:
        targets = all_targets.get(prof.slug, [])
        if not targets:
            continue
        entries = sorted({t[0] for t in targets})
        entry_sql = ", ".join(str(e) for e in entries)
        lines.append(
            f"-- {prof.name}: {len(entries)} NPCs -> TrainerId {prof.canonical_trainer_id}"
        )
        lines.append(
            f"UPDATE `creature_default_trainer` SET `TrainerId` = {prof.canonical_trainer_id} "
            f"WHERE `CreatureId` IN ({entry_sql});"
        )
        lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def write_audit_doc(
    all_targets: dict[str, list[tuple[int, str, str, int]]],
    all_spells: dict[str, dict[int, TrainerSpellRow]],
    professions: list[ProfessionConfig],
) -> Path:
    lines = [
        "# Profession Trainers Audit (Tier 0)",
        "",
        "Generated by `scripts/generate-profession-trainer-sql.py`.",
        "",
        "## Selection criteria",
        "",
        "- Non-Apprentice `*Trainer` NPCs on Eastern Kingdoms / Kalimdor (maps 0, 1)",
        "- Secondary: all Cooking / First Aid / Fishing trainers on classic continents",
        "- Darnassus has no Mining / Blacksmithing / Engineering (vanilla-accurate)",
        "",
    ]
    total_npcs = sum(len(v) for v in all_targets.values())
    total_spells = sum(len(v) for v in all_spells.values())
    lines.append(f"**Total NPCs:** {total_npcs} | **Total template spells:** {total_spells}")
    lines.append("")

    for prof in professions:
        targets = all_targets.get(prof.slug, [])
        spells = all_spells.get(prof.slug, {})
        wrappers = [s for s in prof.rank_wrappers if s in spells]
        lines.append(f"## {prof.name} (TrainerId {prof.canonical_trainer_id})")
        lines.append("")
        lines.append(f"- Skill line: {prof.skill_line}")
        lines.append(f"- NPC count: {len(targets)}")
        lines.append(f"- Template spells: {len(spells)}")
        lines.append(f"- Rank wrappers present: {len(wrappers)}/{len(prof.rank_wrappers)}")
        if wrappers:
            lines.append(f"- Wrappers: {', '.join(str(w) for w in wrappers)}")
        lines.append("")
        lines.append("### NPCs")
        lines.append("")
        lines.append("| Entry | Name | Subname | Current TrainerId |")
        lines.append("|-------|------|---------|-------------------|")
        for entry, name, subname, tid in targets:
            lines.append(f"| {entry} | {name} | {subname} | {tid} |")
        lines.append("")
        lines.append("### Spell manifest")
        lines.append("")
        lines.append("| SpellId | ReqSkillLine | ReqSkillRank | ReqLevel | MoneyCost |")
        lines.append("|---------|--------------|--------------|----------|-----------|")
        for row in sorted(spells.values(), key=lambda r: (r.req_skill_line, r.req_skill_rank, r.spell_id)):
            lines.append(
                f"| {row.spell_id} | {row.req_skill_line} | {row.req_skill_rank} | "
                f"{row.req_level} | {row.money_cost} |"
            )
        lines.append("")

    AUDIT_DOC.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_DOC.write_text("\n".join(lines), encoding="utf-8")
    return AUDIT_DOC


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()

    creatures = parse_creature_templates(AC_WORLD / "creature_template.sql")
    trainer_types = load_trainer_types(AC_WORLD / "trainer.sql")
    by_tid = load_trainer_spells(AC_WORLD / "trainer_spell.sql")
    cdt = load_creature_default_trainers(AC_WORLD / "creature_default_trainer.sql")
    spawn_maps = load_spawn_maps(AC_WORLD / "creature.sql")
    scroll_spells = load_scroll_taught_spells(AC_WORLD / "item_template.sql")

    all_trainer_spell_ids = {
        row.spell_id
        for rows in by_tid.values()
        for row in rows
    }

    all_targets: dict[str, list[tuple[int, str, str, int]]] = {}
    all_spells: dict[str, dict[int, TrainerSpellRow]] = {}

    for cfg in PROFESSIONS:
        targets = collect_target_npcs(cfg, creatures, cdt, trainer_types, spawn_maps)
        spells = build_golden_template(cfg, by_tid, scroll_spells, all_trainer_spell_ids)
        all_targets[cfg.slug] = targets
        all_spells[cfg.slug] = spells
        print(
            f"{cfg.name}: {len(targets)} NPCs, {len(spells)} spells, "
            f"wrappers {sum(1 for w in cfg.rank_wrappers if w in spells)}/{len(cfg.rank_wrappers)}"
        )

    write_audit_doc(all_targets, all_spells, PROFESSIONS)

    if not args.audit_only:
        CUSTOM_SQL.mkdir(parents=True, exist_ok=True)
        for cfg in PROFESSIONS:
            write_profession_sql(cfg, all_spells[cfg.slug])
        write_remap_sql(all_targets, PROFESSIONS)
        print(f"Wrote SQL to {CUSTOM_SQL}")
    print(f"Wrote audit to {AUDIT_DOC}")


if __name__ == "__main__":
    main()
