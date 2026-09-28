"""Extract the name tables tran uses from the C sources into names.json.

Run from the py_json directory:  uv run python tools/gen_names.py
The generated file is checked in so the converter has no build-time dependency
on the C tree; re-run this when src/constants.c or src/h/spell_list.h change.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
OUT = Path(__file__).resolve().parents[1] / "src" / "prworld" / "names.json"

TABLES = {
    # name: file
    "dirs": "constants.c", "room_bits": "constants.c", "exit_bits": "constants.c",
    "immunity_names": "constants.c", "action_bits": "constants.c", "affected_bits": "constants.c",
    "wear_bits": "constants.c", "extra_bits": "constants.c", "item_types": "constants.c",
    "material_types": "constants.c", "rarity_types": "constants.c", "weapon_types": "constants.c",
    "damage_types": "constants.c", "drinks": "constants.c", "intrinsics": "constants.c",
    "forms": "constants.c", "sexes": "constants.c", "sector_bits": "constants.c",
    "board_bits": "constants.c", "clan_flags": "constants.c", "trap_eff_flags": "constants.c",
    "race_list": "constants.c", "class_list": "constants.c", "container_bits": "constants.c",
    "effect_join_styles": "constants.c", "effect_message_keys": "constants.c",
    "effect_proc_keys": "constants.c",
    "spells": "h/spell_list.h", "skills": "h/spell_list.h",
    "race_header_types": "cmds3.c",
    "apply_types": "constants.c", "player_bits": "constants.c", "position_types": "constants.c",
    "account_bits": "constants.c", "equipment_types": "constants.c",
    "clan_ranks": "constants.c",
}

# Tables that exist only as #define groups in const.h: (name, regex over the
# macro name, value pattern). The captured group becomes the lower-case name.
DEFINE_TABLES = {
    # FIRE_DAMAGE 0 .. DARKNESS_DAMAGE 9: the damage kinds damage() takes
    "damage_kinds": (r"#define\s+([A-Z]+)_DAMAGE\s+(\d+)\s*//", {"ELECTRICTY": "electricity"}),
    "pulse_types": (r"#define\s+PULSE_TYPE_([A-Z]+)\s+(\d+)", {}),
    "config_bits": (r"#define\s+CONFIG_([A-Z_]+)\s+\(1<<(\d+)\)", {}),
    "log_bits": (r"#define\s+LOG_([A-Z_]+)\s+\(1<<(\d+)\)", {}),
}

# Table entries whose C spelling is not the name of the bit. The #define is
# the authority; the table string is what tran matches against and what the
# game prints, so it is corrected here rather than in the models. Input
# lookup is exact-then-prefix (string_lookup), so the old spellings that
# world sources could use still resolve to the same bit.
NAME_FIXES = {
    # immunity_names[] pads bit 19 with "20"; const.h has IMM_MAGIC (1<<19),
    # tested in fight.c against MAGIC_DAMAGE.
    ("immunity_names", 19): "magic",
    # action_bits[] lists "polymorphed" twice; const.h has ACT_POLYSELF (1<<14)
    # and ACT_POLYOTHER (1<<15).
    ("action_bits", 14): "polymorphed-self",
    ("action_bits", 15): "polymorphed-other",
}

WEAR_POSITIONS = [
    "light", "finger_r", "finger_l", "neck_1", "neck_2", "body", "head", "legs", "feet",
    "hands", "arms", "shield", "about", "waist", "wrist_r", "wrist_l", "wield", "hold",
    "pouch", "wings", "trinket_r", "trinket_l",
]  # WEAR_* / WIELD / HOLD / POUCH in const.h, indexes 0..21

def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"//[^\n]*", "", text)

def c_array(text: str, name: str) -> list[str]:
    m = re.search(r"char\s*\*\s*" + re.escape(name) + r"\s*\[[^\]]*\]\s*=\s*\{", text)
    if not m:
        raise SystemExit(f"table {name} not found")
    body = text[m.end():]
    body = body[:body.index("};")]
    vals = []
    for s in re.findall(r'"((?:[^"\\]|\\.)*)"', body):
        s = s.encode().decode("unicode_escape")
        if s == "\n":
            break
        vals.append(s)
    return vals

def apply_fields(text: str) -> list[dict]:
    m = re.search(r"Schema apply_fields\[\]\s*=\s*\{", text)
    body = text[m.end():]
    body = body[:body.index("};")]
    rows = []
    for line in body.splitlines():
        mm = re.match(r'\s*\{\s*(APPLY_\w+)\s*,\s*(\w+)\s*,\s*"([^"]+)"\s*,\s*(\w+)', line)
        if mm:
            rows.append({"id_name": mm.group(1), "type": mm.group(2), "name": mm.group(3),
                         "list": None if mm.group(4) == "0" else mm.group(4)})
    return rows

def define_table(text: str, pattern: str, fixups: dict[str, str]) -> list[str]:
    found: dict[int, str] = {}
    for m in re.finditer(pattern, text):
        name = fixups.get(m.group(1), m.group(1)).lower()
        found[int(m.group(2))] = name
    if not found:
        raise SystemExit(f"no defines matched {pattern}")
    return [found.get(i, f"bit{i}") for i in range(max(found) + 1)]


def item_type_ids(text: str) -> dict[str, int]:
    ids = {}
    m = re.search(r"enum item_t\s*\{(.*?)\}", text, flags=re.S)
    for mm in re.finditer(r"(ITEM_\w+)\s*=\s*(\d+)", m.group(1)):
        ids[mm.group(1)] = int(mm.group(2))
    return ids

def main() -> None:
    files = {f: strip_comments((SRC / f).read_text(errors="replace")) for f in set(TABLES.values())}
    out = {"tables": {}, "apply_fields": apply_fields(files["constants.c"]),
           "item_type_ids": item_type_ids(strip_comments((SRC / "h/const.h").read_text(errors="replace")))}
    for name, f in TABLES.items():
        out["tables"][name] = c_array(files[f], name)
    for (name, i), fixed in NAME_FIXES.items():
        table = out["tables"][name]
        if i >= len(table):
            raise SystemExit(f"{name}[{i}] does not exist; NAME_FIXES is stale")
        table[i] = fixed
    const_h = strip_comments((SRC / "h/const.h").read_text(errors="replace"))
    raw_const_h = (SRC / "h/const.h").read_text(errors="replace")  # damage kinds are told apart by their // comment
    for name, (pattern, fixups) in DEFINE_TABLES.items():
        out["tables"][name] = define_table(raw_const_h if name == "damage_kinds" else const_h, pattern, fixups)
    out["tables"]["wear_positions"] = WEAR_POSITIONS
    # attack-type numbers above the spell table: weapon TYPE_*, room hazards,
    # remort/item-set affect markers (spells.h). Keyed by number as a string.
    spells_h = strip_comments((SRC / "h/spells.h").read_text(errors="replace"))
    specials = {}
    for m in re.finditer(r"#define\s+(SPELL_WEAPONSPELL|TYPE_[A-Z_]+|ROOM_[A-Z_0-9]+|AFFECT_[A-Z_]+)\s+(\d+)", spells_h):
        name, num = m.group(1), int(m.group(2))
        if 900 <= num < 1000:
            specials[str(num)] = name.replace("SPELL_", "").replace("TYPE_", "").lower() if not name.startswith(("ROOM_", "AFFECT_")) else name.lower()
    out["attack_specials"] = specials
    # REMORT_* flags (const.h) also turn up as affect types, e.g. 301
    out["remort_flags"] = {m.group(2): m.group(1).lower()
                           for m in re.finditer(r"#define\s+REMORT_([A-Z_0-9]+)\s+(\d+)", const_h)}
    out["skill_bases"] = {"PROF_BASE": 5000, "SKILL_BASE": 10000, "MAX_EXIST_SPELL": 240}
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, v in out["tables"].items():
        print(f"{k:22s} {len(v)}")
    print("apply_fields", len(out["apply_fields"]), "item_type_ids", len(out["item_type_ids"]))

if __name__ == "__main__":
    main()
