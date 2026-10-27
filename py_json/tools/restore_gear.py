"""Splice the equipment and inventory of one player save into another.

    uv run python tools/restore_gear.py <base> <donor> <out>

base  : the player's current file (keeps level, exp, quest points, bank,
        affects, everything but objects)
donor : an older save of the same character whose gear is wanted back
out   : the file to write

The gold the donor carried is added to the base's carried gold, since a
death moves carried gold into the corpse with the gear. The donor's kill
list replaces the base's when the base has none (a death frees it).
The result is re-read and checked before it is written.
"""
import struct
import sys
from pathlib import Path

from prworld.players import read_player, Options, EOF_MARK, SUB_OBJECT, WEAR

GOLD, KILLS = 33, 74


def records(data: bytes, name: str):
    opt = Options(records=[])
    p = read_player(data, name, opt)
    return p, [(tag, data[a:b]) for tag, a, b in opt.records]


def main(base_path: str, donor_path: str, out_path: str) -> int:
    base_data, donor_data = Path(base_path).read_bytes(), Path(donor_path).read_bytes()
    base, base_recs = records(base_data, base_path)
    donor, donor_recs = records(donor_data, donor_path)
    if base["name"] != donor["name"]:
        print(f"name mismatch: {base['name']} vs {donor['name']}", file=sys.stderr)
        return 2

    gear = [rec for tag, rec in donor_recs if tag in (SUB_OBJECT, WEAR)]
    donor_kills = [rec for tag, rec in donor_recs if tag == KILLS]
    gold = (base["gold"] or 0) + (donor["gold"] or 0)

    out = bytearray()
    inserted = False
    for tag, rec in base_recs:
        if tag in (SUB_OBJECT, WEAR):
            if not inserted:
                out += b"".join(gear)
                inserted = True
            continue
        if tag == GOLD:
            rec = struct.pack("<HI", GOLD, gold)
        if tag == KILLS and not base["kills"] and donor_kills:
            rec = donor_kills[0]
        out += rec
    if not inserted:
        out += b"".join(gear)
    if not base["kills"] and donor_kills and not any(t == KILLS for t, _ in base_recs):
        out += donor_kills[0]
    out += struct.pack("<H", EOF_MARK)

    result = read_player(bytes(out), out_path, Options())
    skip = {"source", "equipment", "inventory", "gold", "kills", "carry_weight", "carry_volume"}
    for k in base:
        if k not in skip and result.get(k) != base.get(k):
            print(f"field {k} changed: {base.get(k)!r} -> {result.get(k)!r}", file=sys.stderr)
            return 3
    for k in ("equipment", "inventory"):
        if result[k] != donor[k]:
            print(f"{k} does not match the donor", file=sys.stderr)
            return 3
    if result["gold"] != gold:
        print(f"gold is {result['gold']}, wanted {gold}", file=sys.stderr)
        return 3

    Path(out_path).write_bytes(bytes(out))
    print(f"{result['name']}: level {result['level']}, exp {result['exp']}, gold {result['gold']}, "
          f"bank {result['bankgold']}, {len(result['equipment'])} worn slots, "
          f"{len(result['inventory'])} carried, {len(result['kills'])} kill entries, {len(out)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
