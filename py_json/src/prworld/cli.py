"""Command line entry points.

``world2jsonl`` converts every supported world type; ``rooms`` keeps the
original single-type interface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import classes as classes_mod
from . import players as players_mod
from . import zones as zones_mod
from .schemas import TRAN_TYPES
from .tranparse import Context, ConvertError, convert, read_text, split_names

ALL_TYPES = ["sectors", "rooms", "mobs", "objects", "shops", "races", "clans",
             "item_sets", "effects", "skills", "zones", "classes", "players", "accounts"]

OUTPUT_NAMES = {
    "rooms": "rooms.jsonl", "mobs": "mobs.jsonl", "objects": "objects.jsonl",
    "shops": "shops.jsonl", "races": "races.jsonl", "sectors": "sectors.jsonl",
    "clans": "clans.jsonl", "item_sets": "item_sets.jsonl", "effects": "effects.jsonl",
    "skills": "skills.jsonl", "zones": "zones.jsonl", "classes": "classes.jsonl",
    "players": "players.jsonl", "accounts": "accounts.jsonl",
}


def default_world_dir() -> Path:
    # py_json/src/prworld/cli.py -> pr-stuff/world
    return Path(__file__).resolve().parents[3] / "world"


def sector_names(world: Path) -> list[str]:
    """Names from SECT/sectors.current, in vnum order, as the server builds
    ``sector_types`` at boot (sector.c). Rooms validate ``sector`` against it."""
    path = world / "SECT" / "sectors.current"
    if not path.exists():
        return []
    ctx = Context(root=path.parent, type_name="sectors")
    recs = convert(ctx, path, TRAN_TYPES["sectors"][0])
    by_vnum: dict[int, str] = {r["vnum"]: r["name"] or "" for r in recs}
    high = max(by_vnum) if by_vnum else -1
    return [by_vnum.get(i, "#!UNDEFINED!#") for i in range(high + 1)]


def default_players_src() -> Path | None:
    """Newest players_*.tar next to the world directory, if any."""
    root = default_world_dir().parent
    tars = sorted(root.glob("players_*.tar"))
    return tars[-1] if tars else None


def convert_type(type_name: str, world: Path, strict: bool,
                 players_src: Path | None = None, include_secrets: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    if type_name in ("players", "accounts"):
        src = players_src or default_players_src()
        if src is None or not src.exists():
            raise ConvertError("no player backup given (use --players <tar or dir>)")
        opt = players_mod.Options(include_secrets=include_secrets, strict=strict)
        fn = players_mod.convert_players if type_name == "players" else players_mod.convert_accounts
        return fn(src, opt), opt.warnings
    if type_name == "zones":
        return zones_mod.convert_zones(world / "ZONE" / "zone.list", strict)
    if type_name == "classes":
        return classes_mod.convert_classes(world / "CLASSES" / "classes", strict)
    schema, rel = TRAN_TYPES[type_name]
    entry = world / rel
    if not entry.exists():
        raise ConvertError(f"{entry} not found")
    ctx = Context(root=entry.parent, type_name=type_name, strict=strict)
    if type_name == "rooms":
        names = sector_names(world)
        if names:
            ctx.tables["sector_types"] = names
    return convert(ctx, entry, schema), ctx.warnings


def write_jsonl(records: list[dict[str, Any]], out: Path | None, indent: int | None) -> None:
    fh = sys.stdout if out is None else out.open("w", encoding="utf-8")
    try:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, indent=indent))
            fh.write("\n")
    finally:
        if fh is not sys.stdout:
            fh.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Convert Perilous Realms world sources to JSONL, one file per type.")
    ap.add_argument("-w", "--world", type=Path, default=None,
                    help="world source directory (default: ../../world relative to this package)")
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("out"),
                    help="directory for the .jsonl files (default: ./out)")
    ap.add_argument("-t", "--types", default=",".join(ALL_TYPES),
                    help="comma separated subset of: " + ", ".join(ALL_TYPES))
    ap.add_argument("--strict", action="store_true", help="treat every warning as an error, like tran does")
    ap.add_argument("-p", "--players", type=Path, default=None,
                    help="player backup: a .tar or an extracted dir holding stash/ and account/ "
                         "(default: newest players_*.tar beside the world dir)")
    ap.add_argument("--include-secrets", action="store_true",
                    help="keep password hashes in players.jsonl / accounts.jsonl")
    args = ap.parse_args(argv)

    world = args.world or default_world_dir()
    if not world.is_dir():
        print(f"error: world directory {world} not found", file=sys.stderr)
        return 2
    types = [t for t in split_names(args.types)]
    bad = [t for t in types if t not in ALL_TYPES]
    if bad:
        print(f"error: unknown type(s) {bad}", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)

    status = 0
    summary = []
    for t in ALL_TYPES:
        if t not in types:
            continue
        try:
            records, warnings = convert_type(t, world, args.strict, args.players, args.include_secrets)
        except (ConvertError, ValueError, players_mod.FormatError) as e:
            print(f"error: {t}: {e}", file=sys.stderr)
            status = 1
            continue
        out = args.out_dir / OUTPUT_NAMES[t]
        write_jsonl(records, out, None)
        summary.append((t, len(records), len(warnings), out))
    for t, n, w, out in summary:
        print(f"{t:10s} {n:6d} records  {w:4d} warnings  -> {out}", file=sys.stderr)
    return status


def rooms_main(argv: list[str] | None = None) -> int:
    """The original ``rooms`` command: world/ROOM -> rooms.jsonl."""
    ap = argparse.ArgumentParser(description="Convert the Perilous Realms room sources (world/ROOM) to JSONL.")
    ap.add_argument("-i", "--input", type=Path, default=None,
                    help="ALLROOMS include file, or the ROOM directory containing it")
    ap.add_argument("-o", "--output", type=Path, default=Path("rooms.jsonl"),
                    help="output JSONL path (default: rooms.jsonl; '-' for stdout)")
    ap.add_argument("--strict", action="store_true", help="treat every warning as an error, like tran does")
    ap.add_argument("--indent", type=int, default=None, help="pretty-print each record")
    args = ap.parse_args(argv)

    src = args.input or (default_world_dir() / "ROOM")
    if src.is_dir():
        src = src / "ALLROOMS"
    if not src.exists():
        print(f"error: {src} not found", file=sys.stderr)
        return 2
    ctx = Context(root=src.parent, type_name="rooms", strict=args.strict)
    names = sector_names(src.parent.parent)
    if names:
        ctx.tables["sector_types"] = names
    try:
        rooms = convert(ctx, src, TRAN_TYPES["rooms"][0])
    except ConvertError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    write_jsonl(rooms, None if str(args.output) == "-" else args.output, args.indent)
    areas = len({r["area"] for r in rooms})
    print(f"{len(rooms)} rooms from {areas} areas, {len(ctx.warnings)} warnings"
          + ("" if str(args.output) == "-" else f" -> {args.output}"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
