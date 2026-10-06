"""The persisted and compiled-in data the main converters do not cover.

Sources and outputs (see README):

  spells      src/h/spell_func.h + spells.h + constants.c + fight.c   -> spells.jsonl
  commands    src/h/inter.h                                           -> commands.jsonl
  applies     names.json apply_fields                                 -> applies.jsonl
  name_tables names.json tables                                       -> name_tables.jsonl
  messages    world/MISC/messages (fight.c load_messages)             -> messages.jsonl
  socials     world/MISC/actions  (social.c)                          -> socials.jsonl
  help        world/HELP/help_table (help.c build_help_index)         -> help.jsonl
  lockers     lib/LockerSave/locker.<room>.room (lockers.c)           -> lockers.jsonl
  worldsave   lib/WorldSave/zone.<n> (room.save.c, mob.save.c)        -> worldsave.jsonl
  limited     lib/WorldSave/Misc/limited.obj (world.save.c)           -> limited.jsonl
  boards      lib/<vnum>.board (board.c)                              -> boards.jsonl

Everything here is stdlib only, like the rest of the package.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any, Callable

from .attack import attack_name
from .players import (END_OF_LIST, OBJECT, SUB_OBJECT,
                      FormatError, Options, Reader, bits, name_at, read_affect, read_obj_list,
                      read_pulse_affect, read_pulse_cooldown)
from .schemas import TABLES

NAMES: dict[str, Any] = json.loads(Path(__file__).with_name("names.json").read_text(encoding="utf-8"))
SKILL_BASE = NAMES["skill_bases"]["SKILL_BASE"]
PROF_BASE = NAMES["skill_bases"]["PROF_BASE"]

# room.save.c record tags (distinct from the player file's)
EOR, EOL, MOB = 255, 254, 252
# mob.save.c has its own numbering again: inside a saved mob these replace the
# player file's values (object lists nested inside still use objdb.c's, which
# read_obj_list handles).
MOB_EOR, MOB_SUB_OBJECT, MOB_WEAR, MOB_AFFECT = 255, 254, 251, 249
MOB_PULSE_AFFECT, MOB_PULSE_COOLDOWN, MOB_ITEM_SET_ABILITY = 244, 242, 240


class ExtrasError(Exception):
    pass


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


# ---------------------------------------------------------------------------
# spells: the engine's spell/skill table
# ---------------------------------------------------------------------------

_POSITIONS = {"DEA": 0, "MOR": 1, "INC": 2, "STU": 3, "SLE": 4, "RES": 5, "PRY": 6, "SIT": 7, "FIG": 8,
              "STA": 9, "RUN": 10}
_SPLF = {"V": "verbal", "G": "gestures", "A": "noarena", "Q": "noquest"}
_SPLF_LONG = {"SPLF_VERBAL": "verbal", "SPLF_GESTURES": "gestures", "SPLF_NOARENA": "noarena",
              "SPLF_NOQUEST": "noquest"}
_DAMAGE_NAMES = {f"{k.upper() if k != 'electricity' else 'ELECTRICTY'}_DAMAGE": k
                 for k in NAMES["tables"]["damage_kinds"]}
_CATEGORIES = {"HEAL_SPELLS": "heal", "BUFF_SPELLS": "buff", "UTILITY_SPELLS": "utility"}


def _defines(text: str, prefix: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for m in re.finditer(rf"^#define\s+({prefix}\w*)\s+(-?\d+)", text, re.M):
        out.setdefault(m.group(1), int(m.group(2)))
    return out


def _target_macros(header: str) -> dict[str, str]:
    """The two-letter target macros spell_func.h defines over TAR_* bits."""
    out = {}
    for m in re.finditer(r"^#define\s+([A-Z]{2})\s+TAR_(\w+)", header, re.M):
        out[m.group(1)] = m.group(2).lower()
    return out


def _c_string_table(text: str, name: str) -> list[str]:
    """A ``char *name[] = { "a", "b", ... };`` table's strings in order."""
    m = re.search(rf"char\s*\*\s*{re.escape(name)}\s*\[\]\s*=\s*\{{", text)
    if not m:
        return []
    body = text[m.end():text.index("};", m.end())]
    return [bytes(s, "utf-8").decode("unicode_escape") for s in re.findall(r'"((?:[^"\\]|\\.)*)"', body)]


def _rows(body: str) -> list[tuple[int, list[str]]]:
    """``/* n */ { a, b, c, d, e }`` rows of a spell_info / skill_info table."""
    rows = []
    for m in re.finditer(r"/\*\s*(\d+)\s*\*/\s*\{([^}]*)\}", body):
        fields = [f.strip() for f in m.group(2).split(",")]
        rows.append((int(m.group(1)), fields))
    return rows


def _table_body(text: str, name: str) -> str:
    m = re.search(rf"\b{name}\s*\[\]\s*=\s*\{{", text)
    if not m:
        raise ExtrasError(f"{name}[] not found in spell_func.h")
    return text[m.end():text.index("\n};", m.end())]


def _flags(expr: str, table: dict[str, str]) -> list[str]:
    return [table[t] for t in (p.strip() for p in expr.split("|")) if t and t in table]


def _damage_types(fight_c: str, defines: dict[str, int]) -> dict[int, tuple[str | None, str | None]]:
    """GetSpellType: spell number -> (damage kind, category)."""
    m = re.search(r"^int GetSpellType\(int type\)\s*\{", fight_c, re.M)
    if not m:
        return {}
    body = fight_c[m.end():fight_c.index("\n}", m.end())]
    out: dict[int, tuple[str | None, str | None]] = {}
    pending: list[int] = []
    for line in body.splitlines():
        line = line.strip()
        cm = re.match(r"case\s+(\w+)\s*:", line)
        if cm:
            if cm.group(1) in defines:
                pending.append(defines[cm.group(1)])
            continue
        rm = re.match(r"return\s*\(?\s*(\w+)\s*\)?\s*;", line)
        if rm:
            tok = rm.group(1)
            kind = _DAMAGE_NAMES.get(tok)
            cat = _CATEGORIES.get(tok)
            for n in pending:
                out[n] = (kind, cat)
            pending = []
    return out


def convert_spells(src: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    header = _read(src / "h" / "spell_func.h")
    spells_h = _read(src / "h" / "spells.h")
    constants = _read(src / "constants.c")
    fight = _read(src / "fight.c")
    defines = _defines(spells_h, "SPELL_")
    defines.update(_defines(spells_h, "SKILL_"))
    by_number = {}
    for k, v in defines.items():
        by_number.setdefault(v, k)
    targets = _target_macros(header)
    wear_spell = _c_string_table(constants, "spell_wear_off_msg")
    wear_skill = _c_string_table(constants, "spell_skill_wear_off_msg")
    damage = _damage_types(fight, defines)
    spell_names = NAMES["tables"]["spells"]
    skill_names = NAMES["tables"]["skills"]
    records: list[dict[str, Any]] = []

    def one(kind: str, idx: int, fields: list[str]) -> None:
        if len(fields) != 5:
            warnings.append(f"spell_func.h: {kind} row {idx} has {len(fields)} fields")
            return
        number = idx if kind == "spell" else SKILL_BASE + idx
        name = name_at(spell_names if kind == "spell" else skill_names, idx)
        pos = _POSITIONS.get(fields[1])
        rec: dict[str, Any] = {
            "number": number,
            "kind": kind,
            "name": name,
            "id_name": by_number.get(number),
            "beats": int(fields[0]),
            "min_position": name_at(TABLES["position_types"], pos) if pos is not None else fields[1],
            "flags": _flags(fields[2], _SPLF) or _flags(fields[2], _SPLF_LONG),
            "targets": _flags(fields[3], targets),
            "handler": None if fields[4] in ("NULL", "0") else fields[4],
        }
        wear = (wear_spell if kind == "spell" else wear_skill)
        if idx < len(wear) and wear[idx]:
            rec["wear_off"] = wear[idx]
        if number in damage:
            kind_, cat = damage[number]
            if kind_:
                rec["damage_type"] = kind_
            if cat:
                rec["category"] = cat
        records.append(rec)

    for idx, fields in _rows(_table_body(header, "spell_info")):
        one("spell", idx, fields)
    for idx, fields in _rows(_table_body(header, "skill_info")):
        one("skill", idx, fields)
    if strict and warnings:
        raise ExtrasError("; ".join(warnings))
    return records, warnings


# ---------------------------------------------------------------------------
# commands: cmd_info[] in inter.h
# ---------------------------------------------------------------------------

_LEVELS = {f"I{i}": 2000 + i for i in range(1, 12)}
_CMDF = {"CMDF_DISABLED": "disabled", "CMDF_NODISABLE": "nodisable", "CMDF_FLUSH": "flush",
         "CMDF_NOARENA": "noarena", "CMDF_NOMOB": "nomob", "CMDF_NOORDER": "noorder"}


def convert_commands(src: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    text = _read(src / "h" / "inter.h")
    cmd_num = _defines(_read(src / "h" / "cmd_num.h"), "CMD_") if (src / "h" / "cmd_num.h").exists() else {}
    records = []
    for m in re.finditer(r'^\s*\{\s*"([^"]+)"\s*,([^}]*)\}', text, re.M):
        fields = [f.strip() for f in m.group(2).split(",")]
        if len(fields) < 6:
            warnings.append(f"inter.h: command {m.group(1)!r} has {len(fields) + 1} fields")
            continue
        pos, level, handler, priority, flags = fields[:5]
        num = fields[6] if len(fields) > 6 else "0"
        lvl = _LEVELS.get(level)
        if lvl is None:
            lvl = int(level) if re.fullmatch(r"-?\d+", level) else 0
        records.append({
            "cmd": m.group(1),
            "minimum_position": name_at(TABLES["position_types"], _POSITIONS.get(pos, 9)),
            "minimum_level": lvl,
            "handler": None if handler in ("NULL", "0") else handler,
            "priority": int(priority) if re.fullmatch(r"-?\d+", priority) else 0,
            "flags": [] if flags == "NONE" else [_CMDF.get(f.strip(), f.strip()) for f in flags.split("|")],
            "num": cmd_num.get(num, int(num) if re.fullmatch(r"-?\d+", num) else 0),
            "num_name": num if num in cmd_num else None,
        })
    if strict and warnings:
        raise ExtrasError("; ".join(warnings))
    return records, warnings


# ---------------------------------------------------------------------------
# applies, name tables: straight from names.json
# ---------------------------------------------------------------------------

def convert_applies() -> tuple[list[dict[str, Any]], list[str]]:
    return [{"index": i, **row} for i, row in enumerate(NAMES["apply_fields"])], []


def convert_name_tables() -> tuple[list[dict[str, Any]], list[str]]:
    return [{"name": k, "values": v} for k, v in NAMES["tables"].items()], []


# ---------------------------------------------------------------------------
# messages: the combat message file (fight.c load_messages)
# ---------------------------------------------------------------------------

def _fread_strings(text: str, pos: int, n: int) -> tuple[list[str], int]:
    out = []
    for _ in range(n):
        end = text.index("~", pos)
        s = text[pos:end]
        if s.startswith("\n"):
            s = s[1:]
        out.append(s.rstrip("\n"))
        pos = end + 1
    return out, pos


def convert_messages(path: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    text = _read(path)
    pos = 0
    records = []
    ordinal: dict[int, int] = {}
    while True:
        m = re.compile(r"\s*(\S+)").match(text, pos)
        if not m or m.group(1) != "M":
            break
        pos = m.end()
        m2 = re.compile(r"\s*(-?\d+)").match(text, pos)
        if not m2:
            raise ExtrasError(f"{path}: attack type expected at {pos}")
        atype = int(m2.group(1))
        pos = m2.end()
        strings, pos = _fread_strings(text, pos, 12)
        ordinal[atype] = ordinal.get(atype, 0) + 1
        rec = {"attack_type": atype, "attack_name": attack_name(atype), "ordinal": ordinal[atype]}
        for i, key in enumerate(("die", "miss", "hit", "god")):
            a, v, r = strings[3 * i:3 * i + 3]
            rec[key] = {"attacker_msg": a, "victim_msg": v, "room_msg": r}
        records.append(rec)
    return records, []


# ---------------------------------------------------------------------------
# socials: the actions file (social.c)
# ---------------------------------------------------------------------------

def convert_socials(path: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    lines = _read(path).split("\n")
    i = 0
    records = []
    positions = TABLES["position_types"]

    def action(line: str) -> str | None:
        return None if line.startswith("#") else line

    while i < len(lines):
        line = lines[i].rstrip("\r")
        i += 1
        if not line.strip() or line.startswith("//"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 5:
            warnings.append(f"{path.name}:{i}: bad social header {line!r}")
            continue
        cmd, abbrev, hide, min_ch, min_vict = parts[:5]
        rec: dict[str, Any] = {
            "command": cmd, "abbrev": abbrev, "hide": hide.lower() == "yes",
            "min_position": min_ch if min_ch in positions else min_ch,
            "min_victim_position": min_vict if min_vict in positions else min_vict,
        }
        if len(parts) > 5 and parts[5]:
            rec["min_level"] = int(parts[5])
        keys = ["char_no_arg", "others_no_arg", "char_found"]
        for k in keys:
            rec[k] = action(lines[i].rstrip("\r")) if i < len(lines) else None
            i += 1
        if rec["char_found"] is not None:
            for k in ("others_found", "vict_found", "not_found", "char_auto", "others_auto"):
                rec[k] = action(lines[i].rstrip("\r")) if i < len(lines) else None
                i += 1
        records.append(rec)
    if strict and warnings:
        raise ExtrasError("; ".join(warnings))
    return records, warnings


# ---------------------------------------------------------------------------
# help: help_table (help.c build_help_index, new format)
# ---------------------------------------------------------------------------

_HELP_SECTION = {".usage": "usage", ".useage": "usage", ".xrefs": "xrefs", ".xref": "xrefs", ".xfref": "xrefs"}


def convert_help(path: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    """help_table: ``.begin`` / directives (``.topics``, ``.absminlevel``) /
    keyword line / sections tagged ``.usage``, ``.xrefs``, ``.text`` in any
    order / up to the next ``.begin`` or ``.end``. The C only recognises
    ``.text`` as the body and logs the others, but ``do_help`` renders the
    usage and xrefs sections, so they are kept apart here."""
    warnings: list[str] = []
    lines = [ln.rstrip("\r") for ln in _read(path).split("\n")]
    records: list[dict[str, Any]] = []
    skipped = 0
    i = 0
    while i < len(lines) and not lines[i].startswith(".begin"):
        i += 1
    n = len(lines)
    while i < n:
        if not (lines[i].startswith(".begin") or lines[i].startswith(".being")):
            i += 1
            continue
        first = i + 1
        i += 1
        topics: list[str] = []
        min_level = 0
        keywords: list[str] = []
        sections: dict[str, list[str]] = {}
        current: str | None = None
        while i < n and not (lines[i].startswith(".begin") or lines[i].startswith(".being")
                             or lines[i].startswith(".end")):
            ln = lines[i]
            tag = ln.split()[0] if ln.startswith(".") and ln.split() else ("." if ln.startswith(".") else None)
            if tag is not None:
                if tag.startswith(".absminlev") or tag.startswith(".minlev"):
                    m = re.search(r"\d+", ln)
                    if m:
                        min_level = int(m.group())
                    else:
                        warnings.append(f"{path.name}:{i + 1}: bad level directive {ln!r}")
                elif tag.startswith(".topic") or tag == ".topcs":
                    topics += ln.split()[1:]
                elif tag in _HELP_SECTION:
                    current = _HELP_SECTION[tag]
                    sections.setdefault(current, [])
                elif tag == ".text":
                    current = "text"
                    sections.setdefault(current, [])
                elif tag == ".":
                    if current is not None:
                        sections[current].append(ln)
                else:
                    warnings.append(f"{path.name}:{i + 1}: unknown directive {ln!r}")
            elif current is None:
                if not keywords:
                    keywords = ln.split()
                else:   # body without a .text tag: the C treats everything after the keywords as text
                    current = "text"
                    sections.setdefault(current, []).append(ln)
            else:
                sections[current].append(ln)
            i += 1
        if not keywords:
            skipped += 1
            continue
        rec: dict[str, Any] = {"keywords": keywords, "topics": topics, "min_level": min_level,
                               "text": "\n".join(sections.get("text", [])).rstrip("\n")}
        for k in ("usage", "xrefs"):
            if k in sections:
                rec[k] = "\n".join(sections[k]).rstrip("\n")
        records.append(rec)
    if skipped:
        warnings.append(f"{path.name}: {skipped} .begin blocks without a keyword line (banners) skipped")
    if strict and warnings:
        raise ExtrasError("; ".join(warnings))
    return records, warnings


# ---------------------------------------------------------------------------
# lockers: LockerSave/locker.<room>.room (lockers.c)
# ---------------------------------------------------------------------------

def _locker_items(r: Reader, opt: Options) -> list[dict[str, Any]]:
    """A flat ``OBJECT ... OBJECT END_OF_LIST`` list, nested contents allowed."""
    return read_obj_list(r, opt)


def convert_lockers(lib: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    opt = Options(strict=strict)
    records = []
    d = lib / "LockerSave"
    for f in sorted(d.glob("locker.*.room")) if d.is_dir() else []:
        room = int(f.name.split(".")[1])
        r = Reader(f.read_bytes(), f.name)
        records.append({"room": room, "source": f.name, "items": _locker_items(r, opt)})
    return records, opt.warnings


# ---------------------------------------------------------------------------
# worldsave: WorldSave/zone.<n> (room.save.c WriteRoom, mob.save.c SaveMob)
# ---------------------------------------------------------------------------

_MOB_STATS = {4: "strength", 5: "intelligence", 6: "wisdom", 7: "dexterity", 8: "constitution",
              9: "charisma", 10: "luck"}
_MOB_CUR = {11: "strength", 12: "intelligence", 13: "wisdom", 14: "dexterity", 15: "constitution",
            16: "charisma", 17: "luck"}
_MOB_PEN = {50: "fire", 51: "cold", 52: "electricity", 53: "water", 54: "acid", 55: "poison",
            56: "force", 57: "magic", 58: "light", 59: "darkness"}


# struct char_data fields SaveMob writes that the player file never does, so
# player_layout.json has no entry: their C types from h/structs.h.
_MOB_ONLY = {"ch.vnum": "s32", "ch.extradam": "s32", "ch.default_zone": "s16", "ch.bindpoint": "u32",
             "ch.attacks_per_round": "f64", "ch.base_melee_penetration": "f64", "ch.base_spell_power": "f64",
             "ch.life_steal": "f64", "ch.spell_casting_vamp": "f64", "ch.regens.hp": "s32",
             "ch.regens.mana": "s32", "ch.regens.power": "s32"}
for _k in ("fire", "cold", "electricity", "water", "acid", "poison", "force", "magic", "light", "darkness"):
    _MOB_ONLY[f"ch.base_spell_penetration.{_k}"] = "s32"


def read_saved_mob(r: Reader, opt: Options) -> dict[str, Any]:
    """One SaveMob record: the MOB tag has been consumed; ends at EOR."""
    from .players import LAYOUT

    def f(key: str) -> Any:
        if key in LAYOUT:
            return r.field(key)
        return r.num(_MOB_ONLY[key])
    m: dict[str, Any] = {"base_stats": {}, "stats": {}, "base_spell_penetration": {}, "regens": {},
                         "equipment": {}, "inventory": [], "affects": [], "pulse_affects": [],
                         "pulse_cooldowns": []}

    def setf(name: str, key: str) -> Callable[[], None]:
        return lambda: m.__setitem__(name, f(key))

    def wear() -> None:
        pos = r.u16()
        r.u16()   # SUB_OBJECT
        items = read_obj_list(r, opt)
        m["equipment"][str(name_at(TABLES["wear_positions"], pos))] = items

    handlers: dict[int, Callable[[], Any]] = {
        1: setf("vnum", "ch.vnum"), 2: setf("weight", "ch.weight"), 3: setf("height", "ch.height"),
        18: setf("mana", "ch.mana"), 19: setf("max_mana", "ch.max_mana"),
        20: setf("hit", "ch.hit"), 21: setf("max_hit", "ch.max_hit"),
        22: setf("move", "ch.move"), 23: setf("max_move", "ch.max_move"),
        24: setf("gold", "ch.gold"), 25: setf("exp", "ch.exp"),
        26: setf("hit_bonus", "ch.hit_bonus"), 27: setf("dam_bonus", "ch.dam_bonus"),
        28: lambda: m.__setitem__("resist", bits(f("ch.M_resist"), TABLES["immunity_names"])),
        29: lambda: m.__setitem__("immune", bits(f("ch.M_immune"), TABLES["immunity_names"])),
        30: lambda: m.__setitem__("susceptible", bits(f("ch.susc"), TABLES["immunity_names"])),
        31: lambda: m.__setitem__("attacks_per_round_old", r.s32()),
        32: lambda: m.__setitem__("affected_by", _ext_bits(f("ch.affected_by"))),
        33: lambda: m.__setitem__("position", name_at(TABLES["position_types"], f("ch.position"))),
        34: lambda: m.__setitem__("act", bits(f("ch.act"), TABLES["action_bits"])),
        35: lambda: m.__setitem__("apply_saving_throw", r.array(LAYOUT["ch.apply_saving_throw"]["kind"])),
        36: lambda: m.__setitem__("armor", r.array(LAYOUT["ch.armor"]["kind"])),
        37: lambda: m.__setitem__("stopping", r.array(LAYOUT["ch.stopping"]["kind"])),
        38: setf("carry_weight", "ch.carry_weight"), 39: setf("carry_volume", "ch.carry_volume"),
        40: setf("power", "ch.power"), 41: setf("max_power", "ch.max_power"),
        42: lambda: m.__setitem__("birth", r.num("s64")),   # Write(42, time_t)
        43: setf("default_zone", "ch.default_zone"),
        44: lambda: m.__setitem__("story_teller", r.sd()),
        45: lambda: m.__setitem__("base_armor", r.array(LAYOUT["ch.base_armor"]["kind"])),
        46: lambda: m.__setitem__("base_stopping", r.array(LAYOUT["ch.base_stopping"]["kind"])),
        47: setf("bindpoint", "ch.bindpoint"), 48: setf("attacks_per_round", "ch.attacks_per_round"),
        49: setf("base_melee_penetration", "ch.base_melee_penetration"),
        60: setf("base_spell_power", "ch.base_spell_power"), 61: setf("life_steal", "ch.life_steal"),
        62: setf("extradam", "ch.extradam"), 63: setf("spell_casting_vamp", "ch.spell_casting_vamp"),
        64: lambda: m["regens"].__setitem__("hp", f("ch.regens.hp")),
        65: lambda: m["regens"].__setitem__("mana", f("ch.regens.mana")),
        66: lambda: m["regens"].__setitem__("power", f("ch.regens.power")),
        67: setf("hit_shield", "ch.hit_shield"), 68: setf("remort_count", "ch.remort_count"),
        69: setf("rage", "ch.rage"), 70: setf("energy", "ch.energy"),
        MOB_SUB_OBJECT: lambda: m.__setitem__("inventory", read_obj_list(r, opt)),
        MOB_WEAR: wear,
        MOB_AFFECT: lambda: m["affects"].append(read_affect(r)),
        MOB_PULSE_AFFECT: lambda: m["pulse_affects"].append(read_pulse_affect(r)),
        MOB_PULSE_COOLDOWN: lambda: m["pulse_cooldowns"].append(read_pulse_cooldown(r)),
    }
    for tag, name in _MOB_STATS.items():
        handlers[tag] = (lambda n: lambda: m["base_stats"].__setitem__(n, f(f"ch.base_stats.{n}")))(name)
    for tag, name in _MOB_CUR.items():
        handlers[tag] = (lambda n: lambda: m["stats"].__setitem__(n, f(f"ch.stats.{n}")))(name)
    for tag, name in _MOB_PEN.items():
        handlers[tag] = (lambda n: lambda: m["base_spell_penetration"].__setitem__(
            n, f(f"ch.base_spell_penetration.{n}")))(name)
    while True:
        tag = r.u16()
        if tag == MOB_EOR:
            break
        h = handlers.get(tag)
        if h is None:
            raise FormatError(f"{r.where}: unknown mob save tag {tag} at {r.pos - 2}")
        h()
    for k in ("base_stats", "stats", "base_spell_penetration", "regens", "equipment"):
        if not m[k]:
            del m[k]
    for k in ("inventory", "affects", "pulse_affects", "pulse_cooldowns"):
        if not m[k]:
            del m[k]
    return m


def _ext_bits(words: list[int]) -> list[str]:
    from .players import ext_bits
    return ext_bits(words, TABLES["affected_bits"])


def read_saved_room(r: Reader, opt: Options) -> dict[str, Any] | None:
    if r.eof():
        return None
    number = r.s32()
    room: dict[str, Any] = {"vnum": number, "exits": [], "mobs": [], "items": []}
    while True:
        tag = r.u16()
        if tag == EOR:
            break
        if tag == 0:
            num = r.u16()
            ex: dict[str, Any] = {"num": num}     # exit number; named exits (go/enter) are >= 10
            if num < len(TABLES["dirs"]):
                ex["direction"] = TABLES["dirs"][num]
            while True:
                t = r.u16()
                if t == EOL:
                    break
                if t == 1:
                    ex["info"] = bits(r.u32(), TABLES["exit_bits"])
                elif t == 2:
                    ex["crack_code"] = r.s32()
                elif t == 3:
                    ex["crack_attempts"] = r.s32()
                else:
                    raise FormatError(f"{r.where}: unknown exit tag {t} at {r.pos - 2}")
            room["exits"].append(ex)
        elif tag == 1:
            room["flags"] = bits(r.u32(), TABLES["room_bits"])
        elif tag == MOB:
            room["mobs"].append(read_saved_mob(r, opt))
        elif tag == SUB_OBJECT:
            room["items"] = read_obj_list(r, opt)
        else:
            raise FormatError(f"{r.where}: unknown room save tag {tag} at {r.pos - 2}")
    for k in ("exits", "mobs", "items"):
        if not room[k]:
            del room[k]
    return room


def convert_worldsave(lib: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    opt = Options(strict=strict)
    records = []
    d = lib / "WorldSave"
    files = sorted(d.glob("zone.*"), key=lambda p: int(p.name.split(".")[1])) if d.is_dir() else []
    for f in files:
        zone = int(f.name.split(".")[1])
        r = Reader(f.read_bytes(), f.name)
        if r.u16() != MOB:   # SaveZone writes a u16 252 file header first
            raise FormatError(f"{f.name}: missing zone save header")
        rooms = []
        while True:
            room = read_saved_room(r, opt)
            if room is None:
                break
            rooms.append(room)
        records.append({"zone": zone, "source": f.name, "rooms": rooms})
    return records, opt.warnings


def convert_limited(lib: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    f = lib / "WorldSave" / "Misc" / "limited.obj"
    if not f.exists():
        return [], []
    data = f.read_bytes()
    records = []
    pos = 0
    while pos + 6 <= len(data):
        vnum, count = struct.unpack_from("<ih", data, pos)   # _Write(vnum) s32, _Write(world_count) s16
        records.append({"vnum": vnum, "count": count})
        pos += 6
    warnings = [] if pos == len(data) else [f"{f.name}: {len(data) - pos} trailing bytes"]
    return records, warnings


# ---------------------------------------------------------------------------
# boards: <vnum>.board (board.c)
# ---------------------------------------------------------------------------

def convert_boards(lib: Path, strict: bool) -> tuple[list[dict[str, Any]], list[str]]:
    records = []
    for f in sorted(lib.glob("*.board")):
        if not f.stem.isdigit():
            continue
        data = f.read_bytes()
        pos = 0
        (n,) = struct.unpack_from("<i", data, pos)
        pos += 4
        msgs = []
        for _ in range(n):
            (ln,) = struct.unpack_from("<i", data, pos)
            pos += 4
            head = data[pos:pos + ln].decode("latin-1")
            pos += ln + 1
            (ln,) = struct.unpack_from("<i", data, pos)
            pos += 4
            body = data[pos:pos + ln].decode("latin-1")
            pos += ln + 1
            msgs.append({"header": head, "body": body})
        records.append({"vnum": int(f.stem), "source": f.name, "messages": msgs})
    return records, []
