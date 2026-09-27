"""Attack types: the one numbering space damage() and the messages file use.

Numbers below MAX_EXIST_SPELL are spells; 5000+ are weapon proficiencies
(PROF_BASE); 10000+ are skills (SKILL_BASE); 900-999 are the weapon TYPE_*,
room hazard ROOM_* and affect-marker constants from spells.h; negatives are
per-feature specials (traps: -2 teleport, -3 sleep; -1 undefined).
"""

from __future__ import annotations

from typing import Any

from .schemas import NAMES, TABLES

SPECIALS: dict[int, str] = {int(k): v for k, v in NAMES.get("attack_specials", {}).items()}
REMORT: dict[int, str] = {int(k): v for k, v in NAMES.get("remort_flags", {}).items()}
PROF_BASE = NAMES.get("skill_bases", {}).get("PROF_BASE", 5000)
SKILL_BASE = NAMES.get("skill_bases", {}).get("SKILL_BASE", 10000)
MAX_EXIST_SPELL = NAMES.get("skill_bases", {}).get("MAX_EXIST_SPELL", 240)
NEGATIVE = {-1: "undefined", -2: "teleport", -3: "sleep"}


def attack_type(n: int | None) -> dict[str, Any] | None:
    """{"number", "kind", "name"} for an attack-type number."""
    if n is None:
        return None
    if n < 0:
        return {"number": n, "kind": "special", "name": NEGATIVE.get(n, f"#{n}")}
    if n >= SKILL_BASE:
        i = n - SKILL_BASE
        t = TABLES["skills"]
        return {"number": n, "kind": "skill", "name": t[i] if i < len(t) else f"#{n}"}
    if n >= PROF_BASE:
        i = n - PROF_BASE
        t = TABLES["weapon_types"]
        return {"number": n, "kind": "proficiency", "name": t[i] if i < len(t) else f"#{n}"}
    if n in SPECIALS:
        name = SPECIALS[n]
        kind = "weapon" if 906 <= n <= 918 else "room" if name.startswith("room_") else "marker"
        return {"number": n, "kind": kind, "name": name}
    if n < MAX_EXIST_SPELL:
        t = TABLES["spells"]
        return {"number": n, "kind": "spell", "name": t[n] if n < len(t) and t[n] else f"#{n}"}
    if n in REMORT:
        return {"number": n, "kind": "remort", "name": REMORT[n]}
    return {"number": n, "kind": "unknown", "name": f"#{n}"}


def attack_name(n: int | None) -> str | None:
    a = attack_type(n)
    return None if a is None else a["name"]
