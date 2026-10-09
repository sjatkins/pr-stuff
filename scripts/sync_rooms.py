#!/usr/bin/env python3
"""Bring builders' in-game room edits from live/lib into the world repo.

Where the edits are (see explorations/live-directory.org):

  lib/Area/<builder>   binary, written by the `rsave` command
  lib/UPDATE/*         the same binary files, copied there by hand
  lib/WORLD/<name>     text, written by `tsave <name> lo hi` or `saveworld`

The binary files are converted with src/room2tran, which must be run from
inside lib/ (it reads area.list, zone.out and sector.out from the current
directory) and writes text under lib/TextSave/.

Every text file is then split into room blocks, each block is given its
absolute vnum, and the block is compared with the one for that vnum in
world/ROOM/<area>.room. The report lists rooms that are new, changed or
unchanged. With --write, changed blocks are replaced and new blocks are
appended in the repo file; nothing is ever deleted. Review with git diff
in world/ afterwards, then commit and run world/compile.

`saveworld` (I10) writes every area as WORLD/<area> from the area's real
base, plus WORLD/world as the include list: a text dump of the whole
running world in repo format. Those files are used when they are in
area.list and were written in the same pass as WORLD/world (same
timestamp). Note saveworld never writes the last area in area.list.

A `tsave` file numbers its rooms from the `lo` that was typed and has no
#offset line, so nothing in the file says which rooms it holds, and a
second tsave to the same name replaces the first. Such a file is skipped
unless you pass --base NAME=VNUM with the lo that was typed; the server
log has it as "Saving NAME (lo-hi)". The binary rsave files carry absolute
vnums and need no such help.

Usage:
  sync_rooms.py [--lib DIR] [--world DIR] [--room2tran PATH]
                [--base NAME=VNUM ...] [--write] [FILE ...]

With no FILE arguments every file in lib/Area, lib/UPDATE and lib/WORLD is
used. Files ending in .bak or .old are ignored.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PR_HOME = Path(os.environ.get("PR_HOME", HERE.parent))


# --------------------------------------------------------------------------
# area.list: area name -> base vnum


def read_area_list(path: Path) -> dict[str, int]:
    areas: dict[str, int] = {}
    for line in path.read_text(errors="replace").splitlines():
        match = re.match(r"#define\s+(\S+)\s+(\d+)", line)
        if match:
            areas[match.group(1)] = int(match.group(2))
    return areas


def area_for_vnum(areas: dict[str, int], vnum: int) -> str:
    """The area whose base is the largest one not above vnum."""
    best_name, best_base = "", -1
    for name, base in areas.items():
        if best_base < base <= vnum:
            best_name, best_base = name, base
    return best_name


# --------------------------------------------------------------------------
# room files: text -> list of (vnum, block text)


def balanced_block(text: str, start: int) -> int:
    """Index just past the '}' that closes the '{' at text[start]."""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise ValueError("unbalanced braces")


BLOCK_START = re.compile(r"^(\d+)\s*\n\s*\{", re.M)


def split_rooms(text: str) -> tuple[str, list[tuple[int, str]]]:
    """Return (header, [(local number, block text)]).

    The header is everything before the first room (#offset, defines,
    comments). Each block text is "N\n{...}\n" exactly as written.
    """
    rooms: list[tuple[int, str]] = []
    first = BLOCK_START.search(text)
    header = text[: first.start()] if first else text
    pos = first.start() if first else len(text)
    while pos < len(text):
        match = BLOCK_START.search(text, pos)
        if not match:
            break
        brace = text.index("{", match.end() - 1)
        end = balanced_block(text, brace)
        rooms.append((int(match.group(1)), text[match.start() : end].rstrip("\n") + "\n"))
        pos = end
    return header, rooms


def offset_name(header: str) -> str | None:
    match = re.search(r"^#offset\s+(\S+)", header, re.M)
    return match.group(1) if match else None


# A block's room number and its plain-number exit and teleport targets are
# all relative to the same base. Shifting a block from one base to another
# means adding the difference to each of them. Targets written as Area:n
# are absolute and left alone.

TO_TARGET = re.compile(r"(\bto\s*\{\s*[^,}]+,\s*)(\d+)(\s*\})")
TELE_TARGET = re.compile(r"(\btele\s*\{\s*\d+\s*,\s*\d+\s*,\s*)(\d+)(\s*\})")


def shift_block(block: str, delta: int) -> str:
    if delta == 0:
        return block
    number, rest = block.split("\n", 1)
    rest = TO_TARGET.sub(lambda m: f"{m.group(1)}{int(m.group(2)) + delta}{m.group(3)}", rest)
    rest = TELE_TARGET.sub(lambda m: f"{m.group(1)}{int(m.group(2)) + delta}{m.group(3)}", rest)
    return f"{int(number) + delta}\n{rest}"


def normalised(block: str) -> str:
    """Whitespace-insensitive form for comparing two blocks."""
    return re.sub(r"\s+", " ", block).strip()


# --------------------------------------------------------------------------
# sources in lib/


def convert_binary(room2tran: Path, lib: Path, area_file: Path) -> list[Path]:
    """Run room2tran on one Area/ or UPDATE/ file; return the text files it wrote."""
    textsave = lib / "TextSave"
    textsave.mkdir(exist_ok=True)
    for old in textsave.iterdir():
        old.unlink()
    subprocess.run(
        [str(room2tran), str(area_file.relative_to(lib))],
        cwd=lib, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return sorted(p for p in textsave.iterdir() if p.name != "ALLROOMS")


def from_saveworld(path: Path) -> bool:
    """True if a WORLD/<area> file was written by `saveworld`.

    saveworld writes WORLD/world in the same pass as every area file, so an
    area file written within a few seconds of it is a whole-area dump from
    the area's real base. One written later is a `tsave` of unknown range.
    """
    index = path.parent / "world"
    if path.name == "world" or not index.is_file():
        return False
    return abs(path.stat().st_mtime - index.stat().st_mtime) <= 5


def rooms_from_text(path: Path, areas: dict[str, int], bases: dict[str, int],
                    warnings: list[str]) -> list[tuple[int, str]]:
    """Absolute (vnum, block) pairs from one text room file."""
    header, rooms = split_rooms(path.read_text(errors="replace"))
    name = offset_name(header)
    if name is not None:
        if name not in areas:
            warnings.append(f"{path}: #offset {name} is not in area.list; skipped")
            return []
        base = areas[name]
    elif path.name in bases:
        base = bases[path.name]
    elif from_saveworld(path) and path.name in areas:
        base = areas[path.name]
    else:
        warnings.append(f"{path}: tsave output has no #offset line, and its rooms are "
                        f"numbered from whatever lo was typed, so it is unusable without "
                        f"--base {path.name}=<that lo>; skipped")
        return []
    return [(local + base, block) for local, block in rooms]


# --------------------------------------------------------------------------
# the repo side


class RepoRooms:
    """All world/ROOM/<area>.room files, editable in memory."""

    def __init__(self, room_dir: Path, areas: dict[str, int]):
        self.room_dir = room_dir
        self.areas = areas
        self.text: dict[str, str] = {}           # area -> file text
        self.blocks: dict[int, tuple[str, str]] = {}   # vnum -> (area, block)
        for path in sorted(room_dir.glob("*.room")):
            area = path.stem
            if area not in areas:
                continue
            text = path.read_text(errors="replace")
            self.text[area] = text
            header, rooms = split_rooms(text)
            base = areas[offset_name(header) or area]
            for local, block in rooms:
                self.blocks[local + base] = (area, block)
        self.changed_areas: set[str] = set()

    def area_of(self, vnum: int) -> str:
        """An existing room stays in the file that already holds it; a new
        one goes to the area whose base is nearest below its vnum."""
        current = self.blocks.get(vnum)
        return current[0] if current else area_for_vnum(self.areas, vnum)

    def renumbered(self, vnum: int, block: str) -> str:
        """The block as it must read in its repo file: numbered from that
        area's base instead of from the base of the file it came from."""
        source_base = vnum - int(block.split("\n", 1)[0])
        return shift_block(block, source_base - self.areas[self.area_of(vnum)])

    def place(self, vnum: int, block: str) -> str:
        """Put a block (already renumbered) into the repo.

        Returns "new", "changed" or "same".
        """
        area = self.area_of(vnum)
        current = self.blocks.get(vnum)
        if current is None:
            self.text.setdefault(area, f"#offset {area}\n")
            self.text[area] = self.text[area].rstrip("\n") + "\n\n" + block
            self.blocks[vnum] = (area, block)
            self.changed_areas.add(area)
            return "new"
        if normalised(current[1]) == normalised(block):
            return "same"
        self.text[area] = self.text[area].replace(current[1], block, 1)
        self.blocks[vnum] = (area, block)
        self.changed_areas.add(area)
        return "changed"

    def write(self) -> list[Path]:
        written = []
        for area in sorted(self.changed_areas):
            path = self.room_dir / f"{area}.room"
            path.write_text(self.text[area])
            written.append(path)
        return written


# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--lib", type=Path, default=PR_HOME / "live" / "lib")
    parser.add_argument("--world", type=Path, default=PR_HOME / "world")
    parser.add_argument("--room2tran", type=Path, default=PR_HOME / "src" / "room2tran")
    parser.add_argument("--base", action="append", default=[], metavar="NAME=VNUM",
                        help="base vnum for a tsave file that is not named after an area")
    parser.add_argument("--write", action="store_true", help="change the repo files")
    parser.add_argument("files", nargs="*", type=Path, help="specific files under lib/ to use")
    args = parser.parse_args(argv)

    room_dir = args.world / "ROOM"
    areas = read_area_list(room_dir / "area.list")
    bases: dict[str, int] = {}
    for item in args.base:
        name, _, vnum = item.partition("=")
        bases[name] = int(vnum)

    if args.files:
        sources = [p if p.is_absolute() else args.lib / p for p in args.files]
    else:
        sources = []
        for sub in ("Area", "UPDATE", "WORLD"):
            directory = args.lib / sub
            if directory.is_dir():
                sources += sorted(p for p in directory.iterdir() if p.is_file())
    sources = [p for p in sources if p.suffix not in (".bak", ".old")]
    # Oldest first, so when two files disagree about a room the newest wins
    # and the disagreement is reported below.
    sources.sort(key=lambda p: p.stat().st_mtime)
    if not sources:
        print("nothing to sync: no files in Area/, UPDATE/ or WORLD/")
        return 0

    repo = RepoRooms(room_dir, areas)
    warnings: list[str] = []
    # Pass 1: the newest block for every room, renumbered for the repo.
    wanted: dict[int, tuple[str, str]] = {}   # vnum -> (label, block)
    for source in sources:
        binary = source.parent.name in ("Area", "UPDATE")
        if binary:
            if not args.room2tran.is_file():
                warnings.append(f"{source}: binary file but {args.room2tran} is missing; skipped")
                continue
            text_files = convert_binary(args.room2tran, args.lib, source)
        else:
            text_files = [source]
        for text_file in text_files:
            label = str(source.relative_to(args.lib)) + (f" -> {text_file.name}" if binary else "")
            for vnum, block in rooms_from_text(text_file, areas, bases, warnings):
                block = repo.renumbered(vnum, block)
                earlier = wanted.get(vnum)
                if earlier and normalised(earlier[1]) != normalised(block):
                    warnings.append(f"room {vnum}: {label} disagrees with older {earlier[0]}; "
                                    f"the newer file was used")
                wanted[vnum] = (label, block)

    # Pass 2: compare with the repo and apply.
    counts = {"new": 0, "changed": 0, "same": 0}
    for vnum in sorted(wanted):
        label, block = wanted[vnum]
        result = repo.place(vnum, block)
        counts[result] += 1
        if result != "same":
            print(f"{result:8s} {vnum:7d}  {repo.area_of(vnum)}  ({label})")

    print(f"\n{counts['new']} new, {counts['changed']} changed, {counts['same']} unchanged")
    for warning in warnings:
        print("warning:", warning)
    if not repo.changed_areas:
        return 0
    if args.write:
        for path in repo.write():
            print("wrote", path)
        print("now: cd world && git diff, commit, ./compile, restart")
    else:
        print("dry run; add --write to change", ", ".join(f"ROOM/{a}.room" for a in sorted(repo.changed_areas)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
