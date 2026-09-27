"""Parser for zone reset scripts (world/ZONE/*.zon).

Follows the flex/yacc grammar in ``src/Zone/scanner.l`` and
``src/Zone/parser.y``. ``zone.list`` names the files in compile order.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tranparse import ConvertError, read_text

KEYWORDS = {
    "ZONE": "ZONE", "END": "END", "repeat": "REPEAT", "containing": "CONTAINING",
    "requires": "REQUIRES", "range": "RANGE", "reset": "RESET", "boot_only": "BOOT_ONLY",
    "zone_limit": "ZONE_LIMIT", "always": "ALWAYS", "empty": "EMPTY", "never": "NEVER",
    "mob": "MOB", "obj": "OBJ", "in": "IN", "load": "LOAD", "loadgroup": "LOADGROUP",
    "atmost": "ATMOST", "upto": "UPTO", "with": "WITH", "save": "SAVE",
}

TOKEN_RE = re.compile(
    r"""
    (?P<ws>[ \t\r]+) |
    (?P<nl>\n) |
    (?P<comment>//[^\n]*) |
    (?P<string>"[^"\n]*") |
    (?P<atmost>at\ most) |
    (?P<upto>up\ to) |
    (?P<prob>[0-9]+%) |
    (?P<num>[0-9]+) |
    (?P<or_range>\|-) |
    (?P<and_range>&-|-) |
    (?P<punct>[(){},&|>]) |
    (?P<word>[A-Za-z_][A-Za-z_0-9]*) |
    (?P<bad>.)
    """,
    re.X,
)

LIST_TYPES = {"AND_LIST": "and_list", "OR_LIST": "or_list", "CHAIN_LIST": "chain_list",
              "ANDRANGE": "and_range", "ORRANGE": "or_range"}


@dataclass
class Tok:
    kind: str
    value: Any
    line: int


def tokenize(text: str, where: str) -> list[Tok]:
    toks: list[Tok] = []
    line = 1
    for m in TOKEN_RE.finditer(text):
        k = m.lastgroup
        v = m.group()
        if k == "nl":
            line += 1
        elif k in ("ws", "comment"):
            pass
        elif k == "string":
            toks.append(Tok("STRING", v[1:-1], line))
        elif k == "atmost":
            toks.append(Tok("ATMOST", v, line))
        elif k == "upto":
            toks.append(Tok("UPTO", v, line))
        elif k == "prob":
            toks.append(Tok("PROBABILITY", int(v[:-1]), line))
        elif k == "num":
            toks.append(Tok("NUMBER", int(v), line))
        elif k == "or_range":
            toks.append(Tok("OR_RANGE", v, line))
        elif k == "and_range":
            toks.append(Tok("AND_RANGE", v, line))
        elif k == "punct":
            toks.append(Tok(v, v, line))
        elif k == "word":
            if v in KEYWORDS:
                toks.append(Tok(KEYWORDS[v], v, line))
            else:
                raise ConvertError(f"{where}:{line}: parse error at or before {v!r}")
        else:
            raise ConvertError(f"{where}:{line}: illegal character {v!r}")
    toks.append(Tok("EOF", None, line))
    return toks


class Parser:
    def __init__(self, toks: list[Tok], where: str):
        self.toks = toks
        self.pos = 0
        self.where = where

    # -- helpers -----------------------------------------------------------
    @property
    def cur(self) -> Tok:
        return self.toks[self.pos]

    def at(self, *kinds: str) -> bool:
        return self.cur.kind in kinds

    def take(self, kind: str) -> Tok:
        t = self.cur
        if t.kind != kind:
            raise ConvertError(f"{self.where}:{t.line}: expected {kind}, found {t.value!r}")
        self.pos += 1
        return t

    def error(self) -> ConvertError:
        t = self.cur
        return ConvertError(f"{self.where}:{t.line}: parse error at or before {t.value!r}")

    # -- grammar -----------------------------------------------------------
    def input(self) -> list[dict[str, Any]]:
        zones = []
        while not self.at("EOF"):
            zones.append(self.zone())
        return zones

    def zone(self) -> dict[str, Any]:
        start = self.take("ZONE")
        name = self.take("STRING").value
        z: dict[str, Any] = {
            "name": name, "source": f"{self.where}:{start.line}",
            "range": None, "save": None, "reset": {"type": "never", "frequency": 0},
            "zone_limit": [], "boot_only": [], "commands": [],
        }
        while self.at("RANGE", "SAVE", "RESET", "BOOT_ONLY", "ZONE_LIMIT"):
            self.declaration(z)
        while self.at("REPEAT", "IN"):
            z["commands"].append(self.command())
        self.take("END")
        return z

    def declaration(self, z: dict[str, Any]) -> None:
        k = self.cur.kind
        self.pos += 1
        if k == "RANGE":
            z["range"] = self.list_()
        elif k == "SAVE":
            z["save"] = self.list_()
        elif k == "RESET":
            if self.at("NEVER"):
                self.pos += 1
                z["reset"] = {"type": "never", "frequency": 0}
            else:
                self.take("(")
                kind = self.cur.kind
                if kind not in ("EMPTY", "ALWAYS"):
                    raise self.error()
                self.pos += 1
                self.take(",")
                freq = self.take("NUMBER").value
                self.take(")")
                z["reset"] = {"type": kind.lower(), "frequency": freq}
        elif k == "BOOT_ONLY":
            z["boot_only"] = self.command_list()
        elif k == "ZONE_LIMIT":
            z["zone_limit"] = self.limit_list()

    def limit_list(self) -> list[dict[str, Any]]:
        if self.at("{"):
            self.pos += 1
            out = []
            while not self.at("}"):
                out.append(self.limit())
            self.pos += 1
            return out
        return [self.limit()]

    def limit(self) -> dict[str, Any]:
        n = self.take("NUMBER").value
        if self.at("MOB"):
            kind = "mob"
        elif self.at("OBJ"):
            kind = "obj"
        else:
            raise self.error()
        self.pos += 1
        return {"kind": kind, "max": n, "vnums": self.list_()}

    def command_list(self) -> list[dict[str, Any]]:
        if self.at("{"):
            self.pos += 1
            out = []
            while not self.at("}"):
                out.append(self.command())
            self.pos += 1
            return out
        return [self.command()]

    def command(self) -> dict[str, Any]:
        repeat = 1
        if self.at("REPEAT"):
            self.pos += 1
            repeat = self.take("NUMBER").value
        self.take("IN")
        rooms = self.list_()
        return {"repeat": repeat, "rooms": rooms, "loads": self.sub_command_list()}

    def sub_command_list(self) -> list[dict[str, Any]]:
        if self.at("{"):
            self.pos += 1
            out = []
            while not self.at("}"):
                out.append(self.sub_command())
            self.pos += 1
            return out
        return [self.sub_command()]

    def sub_command(self) -> dict[str, Any]:
        if self.at("LOAD"):
            op = "load"
        elif self.at("LOADGROUP"):
            op = "loadgroup"
        else:
            raise self.error()
        self.pos += 1
        return {"op": op, **self.load_type()}

    def howmany(self) -> dict[str, Any]:
        mod = {"probability": 100, "count": 1, "count_type": "atmost"}
        if self.at("ATMOST"):
            self.pos += 1
            mod["count"] = self.take("NUMBER").value
        elif self.at("UPTO"):
            self.pos += 1
            mod["count"] = self.take("NUMBER").value
            mod["count_type"] = "upto"
        while self.at("PROBABILITY"):
            mod["probability"] = self.cur.value
            self.pos += 1
        return mod

    def load_type(self) -> dict[str, Any]:
        if self.at("("):
            self.pos += 1
            items = [self.load_type()]
            while self.at(">"):
                self.pos += 1
                items.append(self.load_type())
            self.take(")")
            return {"kind": "chain", "items": items}
        mod = self.howmany()
        if self.at("MOB"):
            self.pos += 1
            vnums = self.list_()
            inv = self.objlist() if self._take_if("WITH") else []
            return {"kind": "mob", **mod, "vnums": vnums, "inventory": inv}
        if self.at("OBJ"):
            self.pos += 1
            return self.object_rest(mod)
        raise self.error()

    def object(self) -> dict[str, Any]:
        mod = self.howmany()
        self.take("OBJ")
        return self.object_rest(mod)

    def object_rest(self, mod: dict[str, Any]) -> dict[str, Any]:
        vnums = self.list_()
        contents = self.objlist() if self._take_if("CONTAINING") else []
        requires = self.objlist() if self._take_if("REQUIRES") else []
        return {"kind": "obj", **mod, "vnums": vnums, "contents": contents, "requires": requires}

    def objlist(self) -> list[dict[str, Any]]:
        if self.at("{"):
            self.pos += 1
            out = [self.object()]
            while not self.at("}"):
                out.append(self.object())
            self.pos += 1
            return out
        return [self.object()]

    def _take_if(self, kind: str) -> bool:
        if self.at(kind):
            self.pos += 1
            return True
        return False

    def list_(self) -> dict[str, Any]:
        if self.at("NUMBER"):
            return {"type": "and_list", "values": [self.take("NUMBER").value]}
        self.take("(")
        first = self.take("NUMBER").value
        if self.at("AND_RANGE"):
            self.pos += 1
            lst = {"type": "and_range", "values": [first, self.take("NUMBER").value]}
        elif self.at("OR_RANGE"):
            self.pos += 1
            lst = {"type": "or_range", "values": [first, self.take("NUMBER").value]}
        elif self.at("&", "|", ">"):
            sep = self.cur.kind
            typ = {"&": "and_list", "|": "or_list", ">": "chain_list"}[sep]
            vals = [first]
            while self.at(sep):
                self.pos += 1
                vals.append(self.take("NUMBER").value)
            lst = {"type": typ, "values": vals}
        else:
            lst = {"type": "and_list", "values": [first]}
        self.take(")")
        return lst


def convert_zones(list_file: Path, strict: bool = False) -> tuple[list[dict[str, Any]], list[str]]:
    zones: list[dict[str, Any]] = []
    warnings: list[str] = []
    base = list_file.parent
    for name in read_text(list_file).splitlines():
        name = name.strip()
        if not name:
            continue
        path = base / name
        if not path.exists():
            msg = f"{list_file.name}: can't open {name} for reading"
            if strict:
                raise ConvertError(msg)
            warnings.append(msg)
            print(f"warning: {msg}", file=sys.stderr)
            continue
        toks = tokenize(read_text(path), name)
        zones.extend(Parser(toks, name).input())
    return zones, warnings
