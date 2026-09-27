"""Cross-check the JSONL vnum sets against the binary files tran compiled.

Walks each ``.out`` file using the same schema tables the converter uses,
so it also exercises the schema transcription: a wrong field type shows up
as a stream desync. Run from py_json:  uv run python tools/check_bin.py [out_dir]
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from prworld.schemas import TRAN_TYPES, Schema  # noqa: E402

WORLD = Path(__file__).resolve().parents[2] / "world"

BIN = {
    "rooms": "ROOM/world.out", "mobs": "MOB/mob.out", "objects": "OBJ/obj.out",
    "shops": "SHOP/shop.out", "races": "RACE/race.out", "sectors": "SECT/sector.out",
    "clans": "CLAN/clans.out", "item_sets": "ITEM_SETS/item_sets.out",
}

FIXED = {"U8": 1, "S8": 1, "E8": 1, "S16": 2, "U16": 2, "S32": 4, "U32": 4, "E32": 4,
         "BIT": 4, "ROM": 4, "DBL": 8, "T32": 8, "DIC": 12, "V32": 12, "IDV": 32,
         "VEC": 24, "RVR": 5, "TEL": 9, "EXI": 5, "HOL": 0}
COUNTED = {"STR", "A32", "ADBL", "L16"}  # u16 byte count then payload


class Reader:
    def __init__(self, data: bytes):
        self.d = data
        self.pos = 0

    def u16(self) -> int:
        v = struct.unpack_from("<H", self.d, self.pos)[0]
        self.pos += 2
        return v

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.pos)[0]
        self.pos += 4
        return v

    def eof(self) -> bool:
        return self.pos >= len(self.d)

    def skip_field(self, f, schema_of_sub) -> None:
        t = f.type
        if t in FIXED:
            self.pos += FIXED[t]
        elif t in COUNTED:
            n = self.u16()
            self.pos += n
        elif t == "SUB":
            self.fields(f.sub or (), end=254)
        else:
            raise ValueError(f"cannot size field type {t} ({f.name})")

    def fields(self, schema: Schema, end: int) -> None:
        while not self.eof():
            fid = self.u16()
            if fid == end:
                return
            if fid == 255:  # next record marker: hand it back to the caller
                self.pos -= 2
                return
            if fid == 241:  # END_OF_DATA, written after sub-blocks whose schema has metadata
                continue
            f = next((x for x in schema if x.id == fid), None)
            if f is None:
                raise ValueError(f"unknown field id {fid} at offset {self.pos - 2}")
            self.skip_field(f, None)


def read_vnums(path: Path, schema: Schema) -> list[int]:
    r = Reader(path.read_bytes())
    vnums = []
    while not r.eof():
        mark = r.u16()
        if mark != 255:
            raise ValueError(f"expected record marker at {r.pos - 2}, got {mark}")
        vnums.append(r.u32())
        r.fields(schema, end=-1)
    return vnums


def main() -> int:
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "out")
    bad = 0
    for t, rel in BIN.items():
        binpath = WORLD / rel
        jpath = out_dir / f"{t}.jsonl"
        if not binpath.exists() or not jpath.exists():
            print(f"{t:10s} skipped (missing {binpath.name if not binpath.exists() else jpath.name})")
            continue
        try:
            bv = read_vnums(binpath, TRAN_TYPES[t][0])
        except Exception as e:  # noqa: BLE001
            print(f"{t:10s} binary walk FAILED: {e}")
            bad += 1
            continue
        jv = [json.loads(l)["vnum"] for l in jpath.open(encoding="utf-8")]
        sb, sj = set(bv), set(jv)
        ok = sb == sj and len(bv) == len(jv)
        bad += 0 if ok else 1
        print(f"{t:10s} binary {len(bv):6d}  jsonl {len(jv):6d}  "
              + ("OK" if ok else f"MISMATCH  only-bin={sorted(sb - sj)[:5]} only-json={sorted(sj - sb)[:5]}"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
