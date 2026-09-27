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
}

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
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for k, v in out["tables"].items():
        print(f"{k:22s} {len(v)}")
    print("apply_fields", len(out["apply_fields"]), "item_type_ids", len(out["item_type_ids"]))

if __name__ == "__main__":
    main()
