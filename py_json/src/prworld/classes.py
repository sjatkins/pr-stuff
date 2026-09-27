"""Parser for the class table (world/CLASSES/classes), as read by skills.c boot_class.

The file is a sequence of ``KEY: value`` lines per class, each block introduced
by ``INDEX: n``, followed by ``SKILLS`` / ``SPELLS`` / ``PROF`` tables whose
rows are ``|`` separated columns.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from .schemas import TABLES
from .tranparse import read_text

STATS = ("str", "int", "wis", "dex", "con", "chr", "lck")
SAVES = ("paralysis", "rod", "petrification", "breath", "spell", "extra")
FLAG_NAMES = {
    "F": "fighter", "C": "cleric", "M": "mage", "T": "thief", "I": "immortal",
    "D": "disabled", "B": "basic", "S": "specialist", "X": "multiclass",
}
ALIGN_NAMES = {"n": "neutral", "g": "good", "e": "evil"}


def _ints(text: str, n: int | None = None) -> list[int]:
    vals = [int(x) for x in re.findall(r"[+-]?\d+", text)]
    return vals[:n] if n else vals


def _exact(name: str, table: list[str]) -> bool:
    return any(name.lower() == t.lower() for t in table)


def _new_class(index: int) -> dict[str, Any]:
    return {
        "index": index, "classname": None, "abbrv": None, "align": [], "hp": None,
        "min": None, "max": None, "base": None, "extr": None, "races": [],
        "resists": None, "items": [], "thac0": None, "speed": None, "mult": 1.0,
        "flags": [], "build": None, "desc": None, "title": None, "prof": None,
        "saves": None, "decrease": None, "minsave": None,
        "skills": [], "spells": [], "profs": [],
    }


def _stat_dict(vals: list[int], names: tuple[str, ...]) -> dict[str, int]:
    return {n: v for n, v in zip(names, vals)}


def _table_row(line: str, state: str, where: str, warn) -> dict[str, Any] | None:
    cols = [c.strip() for c in line.split("|")]
    if len(cols) < 6:
        return None
    name = cols[0]
    table = TABLES["spells"] if state == "spells" else TABLES["skills"] if state == "skills" else TABLES["weapon_types"]
    if not _exact(name, table):
        warn(where, f"{state[:-1]} {name!r} not found in the server's name table")
    row: dict[str, Any] = {
        "name": name,
        "min_level": _first_int(cols[1]),
        "difficulty": _first_int(cols[2]),
        "cost": _first_int(cols[3]),
        "max_at_guild": _first_int(cols[4]),
        "max_learn": _first_int(cols[5]),
    }
    rest = cols[6:]
    if state == "spells":
        row["mana"] = _first_int(rest[0]) if rest else 0
        src = rest[1].strip().upper()[:1] if len(rest) > 1 else ""
        row["source"] = {"M": "mana", "P": "power"}.get(src)
        rest = rest[2:]
    prereq = rest[0] if rest else ""
    row["prereqs"] = [p.strip() for p in prereq.split(",") if p.strip()]
    if state == "spells":
        row["components"] = _ints(rest[1]) if len(rest) > 1 else []
    return row


def _first_int(text: str) -> int:
    m = re.search(r"[+-]?\d+", text)
    return int(m.group()) if m else 0


def convert_classes(path: Path, strict: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []

    def warn(where: str, msg: str) -> None:
        text = f"{where}: {msg}"
        if strict:
            raise ValueError(text)
        warnings.append(text)
        print(f"warning: {text}", file=sys.stderr)

    lines = read_text(path).splitlines()
    declared = _first_int(lines[0]) if lines else 0
    classes: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    state = "skills"
    rel = path.name
    for ln, raw in enumerate(lines, 1):
        line = raw.rstrip()
        where = f"{rel}:{ln}"
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()
            if key == "index":
                cur = _new_class(_first_int(val))
                cur["source"] = where
                classes.append(cur)
                state = "skills"
                continue
            if cur is None:
                continue
            if key == "classname":
                cur["classname"] = val
            elif key == "abbrv":
                cur["abbrv"] = val
            elif key == "hp":
                cur["hp"] = _ints(val, 3)
            elif key == "flags":
                cur["flags"] = [FLAG_NAMES.get(c.upper(), c) for c in val if not c.isspace()]
            elif key == "build":
                cur["build"] = val
            elif key == "desc":
                cur["desc"] = val
            elif key == "title":
                cur["title"] = val
            elif key == "prof":
                cur["prof"] = val.split()[0] if val else None
                if cur["prof"] and not _exact(cur["prof"], TABLES["weapon_types"]):
                    warn(where, f"proficiency {cur['prof']!r} not found")
            elif key == "thac0":
                cur["thac0"] = {"level": _first_int(val), "min": _ints(val, 2)[-1] if len(_ints(val)) > 1 else 0}
            elif key == "speed":
                v = _ints(val, 2)
                cur["speed"] = {"level": v[0] if v else 0, "max": v[1] if len(v) > 1 else 0}
            elif key == "mult":
                cur["mult"] = float(val) if val else 1.0
            elif key in ("base", "min", "max"):
                cur[key] = _stat_dict(_ints(val, 7), STATS)
            elif key == "extr":
                v = _ints(val, 8)
                cur["extr"] = _stat_dict(v, STATS + ("max_total",))
            elif key == "resists":
                cur["resists"] = _ints(val)
            elif key in ("saves", "decrease", "minsave"):
                cur[key] = _ints(val)
            elif key == "items":
                cur["items"] = _ints(val)
            elif key == "align":
                cur["align"] = [ALIGN_NAMES[c] for c in val.lower()[:3] if c in ALIGN_NAMES]
            elif key == "races":
                abbrevs = re.findall(r"[A-Za-z]{2}", val)
                cur["races"] = [a[0].upper() + a[1].lower() for a in abbrevs]
                for a in cur["races"]:
                    if not _exact(a, TABLES["race_header_types"]):
                        warn(where, f"race {a!r} not found")
            else:
                warn(where, f"unknown key {key.upper()!r} ignored by the server")
        elif line.startswith("SKILL"):
            state = "skills"
        elif line.startswith("SPELL"):
            state = "spells"
        elif line.startswith("PROF"):
            state = "profs"
        elif "|" in line and cur is not None:
            row = _table_row(line, state, where, warn)
            if row:
                cur[state].append(row)
    if declared != len(classes):
        warn(rel, f"header declares {declared} records but {len(classes)} INDEX blocks found")
    return classes, warnings
