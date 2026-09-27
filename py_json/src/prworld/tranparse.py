"""Schema-driven parser for the brace-block world sources compiled by ``tran``.

This reimplements the text side of ``src/tran/tran.c``: the ``#include`` /
``#define`` / ``#offset`` directives, ``@macro`` definitions and expansion,
numbered ``{ ... }`` records, and the per-field-type value parsing in
``parse_block``. Records come out as plain dicts ready for JSON.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from .schemas import TABLES, F, Schema, find_field

TOKEN_RE = re.compile(r"[A-Za-z0-9_]*")
INT_RE = re.compile(r"\s*([+-]?\d+)")
FLOAT_RE = re.compile(r"\s*([+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)")

DIRS = TABLES["dirs"]


class ConvertError(Exception):
    """A source construct tran would have rejected."""


@dataclass
class Context:
    """Mutable compiler state mirroring the globals in tran.c."""

    root: Path
    type_name: str = ""
    defines: dict[str, int] = field(default_factory=dict)
    offset: int = 0
    offset_name: str | None = None
    macros: dict[str, str] = field(default_factory=dict)
    tables: dict[str, list[str]] = field(default_factory=lambda: dict(TABLES))
    strict: bool = False
    warnings: list[str] = field(default_factory=list)
    seen_vnums: dict[int, str] = field(default_factory=dict)

    def warn(self, where: str, msg: str) -> None:
        text = f"{where}: {msg}"
        if self.strict:
            raise ConvertError(text)
        self.warnings.append(text)
        print(f"warning: {text}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Low-level helpers, each mirroring a tran routine
# ---------------------------------------------------------------------------

def read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def string_lookup(name: str, table: list[str]) -> int:
    """PRLib/utility.c string_lookup: case-insensitive exact, then prefix."""
    lname = name.lower()
    for i, entry in enumerate(table):
        if entry.lower() == lname:
            return i
    if lname:
        for i, entry in enumerate(table):
            if entry.lower().startswith(lname):
                return i
    return -1


def split_names(text: str) -> list[str]:
    """tran_util.c string_table tokenising: comma separated, whitespace trimmed."""
    return [part.strip() for part in text.split(",") if part.strip()]


def parse_str(param: str) -> str:
    """STR fields: trim, then drop one leading and one trailing double quote."""
    s = param.strip()
    if s.startswith('"'):
        s = s[1:]
    if s.endswith('"'):
        s = s[:-1]
    return s


def atoi(text: str) -> int | None:
    m = INT_RE.match(text)
    return int(m.group(1)) if m else None


def atof(text: str) -> float:
    m = FLOAT_RE.match(text)
    return float(m.group(1)) if m else 0.0


def lookup_names(ctx: Context, where: str, param: str, table_name: str | None,
                 what: str) -> list[str]:
    """Comma separated names validated against a table; canonical spelling out."""
    names = split_names(param)
    table = ctx.tables.get(table_name) if table_name else None
    if not table:
        return names
    out = []
    for raw in names:
        idx = string_lookup(raw, table)
        if idx < 0:
            ctx.warn(where, f"unknown {what} {raw!r}")
            out.append(raw)
        else:
            out.append(table[idx])
    return out


def resolve_room(ctx: Context, where: str, arg: str) -> tuple[int | None, str]:
    """tran.c resolve_room: ``AREA:n`` uses that area's define, else the file offset."""
    raw = arg.strip()
    offset = ctx.offset
    num_text = raw
    if ":" in raw:
        area, _, num_text = raw.partition(":")
        area = area.strip()
        if area not in ctx.defines:
            ctx.warn(where, f"unknown area {area!r} in room reference {raw!r}")
            return None, raw
        offset = ctx.defines[area]
    n = atoi(num_text)
    if n is None:
        ctx.warn(where, f"room reference must be AREA:offset or a number, got {raw!r}")
        return None, raw
    return n + offset, raw


def lookup_dir(ctx: Context, where: str, text: str) -> tuple[int | None, str | None]:
    name = text.strip()
    idx = string_lookup(name, DIRS)
    if idx >= 0:
        return idx, DIRS[idx]
    if re.fullmatch(r"\d+", name):
        num = int(name)
        return num, DIRS[num] if num < len(DIRS) else None
    ctx.warn(where, f"unknown direction {name!r}")
    return None, None


def int_list(ctx: Context, where: str, param: str, count: int, what: str) -> list[int | None]:
    """T32 / DIC / V32: ``count`` comma separated integers."""
    parts = param.split(",")
    if len(parts) < count:
        ctx.warn(where, f"{what} requires {count} parameters: {param.strip()!r}")
    vals = [atoi(p) for p in parts[:count]]
    while len(vals) < count:
        vals.append(None)
    return vals


# ---------------------------------------------------------------------------
# Block tokenising (tran.c ReadBlock / SubBlock / process_block)
# ---------------------------------------------------------------------------

def balanced(text: str, start: int, open_: str, close: str) -> tuple[str, int]:
    """Contents of the delimited span opening at ``start`` and the index past it."""
    depth = 1
    i = start + 1
    n = len(text)
    while i < n and depth:
        c = text[i]
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
        i += 1
    if depth:
        raise ConvertError(f"unbalanced {open_}{close} in block")
    return text[start + 1:i - 1], i


def sub_block(text: str, pos: int) -> tuple[str, int]:
    """From ``pos``, skip to the next ``{`` and return its balanced contents.

    Returns (contents, index just past the closing brace). Mirrors SubBlock,
    which does not stop at anything before the opening brace.
    """
    start = text.find("{", pos)
    if start < 0:
        return "", len(text)
    depth = 1
    i = start + 1
    n = len(text)
    while i < n and depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth:
        raise ConvertError("unbalanced braces in block")
    return text[start + 1:i - 1], i


def iter_fields(ctx: Context, where: str, block: str) -> Iterator[tuple[str, str]]:
    """Yield (token, param) pairs the way process_block does."""
    pos = 0
    n = len(block)
    while pos < n:
        while pos < n and block[pos].isspace():
            pos += 1
        if pos >= n:
            break
        m = TOKEN_RE.match(block, pos)
        token = m.group()
        pos = m.end()
        if not token:
            # tran would abort here ("Unrecognized token"). Skip the junk up
            # to the next brace so one stray character does not lose the record.
            junk_end = block.find("{", pos)
            junk = block[pos:junk_end if junk_end >= 0 else n].strip()
            ctx.warn(where, f"unexpected text before field: {junk[:60]!r}")
        # Accept ``field ( value )`` as well as ``field { value }``. tran itself
        # skips ahead to the next ``{`` and loses the value; the sources use
        # parentheses in a handful of places and the intent is clear.
        k = pos
        while k < n and block[k].isspace():
            k += 1
        if k < n and block[k] == "(":
            param, pos = balanced(block, k, "(", ")")
        else:
            brace = block.find("{", pos)
            between = block[pos:brace if brace >= 0 else n]
            if between.strip():
                ctx.warn(where, f"text between field {token!r} and its block is ignored: {between.strip()[:40]!r}")
            param, pos = sub_block(block, pos)
        if token:
            yield token, param


def iter_sub_blocks(text: str) -> Iterator[str]:
    """Anonymous ``{ ... } { ... }`` blocks, as process_array walks them."""
    pos = 0
    while text.find("{", pos) >= 0:
        contents, pos = sub_block(text, pos)
        yield contents


# ---------------------------------------------------------------------------
# Macros (tran.c macro_expand / arg_subst)
# ---------------------------------------------------------------------------

def arg_subst(text: str, args: list[str], where: str) -> str:
    def repl(m: re.Match) -> str:
        n = int(m.group(1))
        if n < 1 or n > len(args):
            raise ConvertError(f"{where}: macro argument ${n} out of range")
        return args[n - 1]
    return re.sub(r"\$(\d+)", repl, text)


def macro_expand(ctx: Context, where: str, text: str, depth: int = 0) -> str:
    if depth > 50:
        raise ConvertError(f"{where}: macro expansion too deep")
    out = []
    i = 0
    n = len(text)
    while i < n:
        j = text.find("@", i)
        if j < 0:
            out.append(text[i:])
            break
        out.append(text[i:j])
        j += 1
        k = j
        while k < n and not text[k].isspace() and text[k] != "(":
            k += 1
        name = text[j:k]
        args: list[str] = []
        if k < n and text[k] == "(":
            close = text.find(")", k)
            if close < 0:
                raise ConvertError(f"{where}: unterminated macro arguments for @{name}")
            args = text[k + 1:close].split(",")
            k = close + 1
        body = None
        for mname, mtext in ctx.macros.items():
            if mname.lower() == name.lower():
                body = mtext
        if body is None:
            raise ConvertError(f"{where}: unknown macro @{name}")
        if "$" in body:
            body = arg_subst(body, args, where)
        out.append(body)
        i = k
    result = "".join(out)
    if "@" in result:
        return macro_expand(ctx, where, result, depth + 1)
    return result


# ---------------------------------------------------------------------------
# Field value parsing (tran.c parse_block)
# ---------------------------------------------------------------------------

def parse_value(ctx: Context, where: str, f: F, param: str) -> Any:
    t = f.type
    p = param.strip()
    if t == "STR":
        return parse_str(param)
    if t in ("U8", "S8", "S16", "U16", "S32", "U32"):
        v = atoi(p)
        if v is None:
            ctx.warn(where, f"{f.name} takes an integer, got {p!r}")
        return v
    if t == "IDX":
        v = atoi(p)
        table = ctx.tables.get(f.list) if f.list else None
        if v is None:
            ctx.warn(where, f"{f.name} takes an integer, got {p!r}")
            return None
        if table and 0 <= v < len(table):
            return table[v]
        ctx.warn(where, f"{f.name}: {v} is not in {f.list}")
        return f"#{v}"
    if t == "ATK":
        from .attack import attack_type
        v = atoi(p)
        if v is None:
            ctx.warn(where, f"{f.name} takes an integer, got {p!r}")
            return None
        return attack_type(v)
    if t == "DBL":
        return atof(p)
    if t in ("E8", "E32"):
        table = ctx.tables.get(f.list) if f.list else None
        if not table:
            return p
        idx = string_lookup(p, table)
        if idx < 0:
            ctx.warn(where, f"{f.name}: {p!r} is not a legal value")
            return p
        return table[idx]
    if t == "ESTR":
        table = ctx.tables.get(f.list) if f.list else None
        if table and string_lookup(p, table) < 0:
            ctx.warn(where, f"{f.name}: {p!r} is not a legal value")
        return p
    if t in ("BIT", "IDV", "L16"):
        return lookup_names(ctx, where, param, f.list, f.name)
    if t in ("SET", "ASTR"):
        return lookup_names(ctx, where, param, f.list, f.name)
    if t == "HASH":
        return parse_hash(ctx, where, f, param)
    if t == "A32":
        return [int(x) for x in re.findall(r"\d+", param)]
    if t == "ADBL":
        return [float(x) for x in re.findall(r"\d+(?:\.\d*)?", param)]
    if t == "T32":
        return int_list(ctx, where, param, 2, f.name)
    if t in ("DIC", "V32"):
        return int_list(ctx, where, param, 3, f.name)
    if t == "VEC":
        return [atof(x) for x in param.split(",")[:3]]
    if t == "RVR":
        parts = p.split(",")
        if len(parts) != 2:
            ctx.warn(where, f"river requires direction and speed: {p!r}")
            return None
        dnum, dname = lookup_dir(ctx, where, parts[0])
        return {"direction": dname, "direction_num": dnum, "speed": atoi(parts[1])}
    if t == "TEL":
        parts = p.split(",")
        if len(parts) != 3:
            ctx.warn(where, f"teleport requires 3 parameters: {p!r}")
            return None
        to, raw = resolve_room(ctx, where, parts[2])
        return {"time": atoi(parts[0]), "look": atoi(parts[1]), "target": to, "target_raw": raw}
    if t == "ROM":
        return resolve_room(ctx, where, p)[0]
    if t == "HOL":
        return None
    if t == "PROC":
        return p
    if t == "SUB":
        return parse_block(ctx, where, f.sub or (), param, top=False)
    if t == "ASUB":
        return [parse_block(ctx, where, f.sub or (), b, top=False) for b in iter_sub_blocks(param)]
    ctx.warn(where, f"unsupported field type {t} for {f.name}")
    return p


def parse_hash(ctx: Context, where: str, f: F, param: str) -> dict[str, str]:
    """tran_util.c string_hash: ``key => value`` pairs separated by commas."""
    out: dict[str, str] = {}
    table = ctx.tables.get(f.list) if f.list else None
    for item in param.split(","):
        if not item.strip():
            continue
        key, sep, value = item.partition("=>")
        key = re.sub(r"\s+", "", key)  # tran drops all whitespace inside the key
        if not sep:
            ctx.warn(where, f"{f.name}: no value specified for key {key!r}")
            continue
        if table and string_lookup(key, table) < 0:
            ctx.warn(where, f"{f.name}: key {key!r} not recognized")
        out[key] = value.strip()
    return out


def parse_exits(ctx: Context, where: str, schema: Schema, block: str,
                exits: list[dict[str, Any]]) -> None:
    """``exits { to {...} keywords {...} ... }``: each ``to`` starts a new exit
    and later fields attach to it (roomdb.c case 7)."""
    cur: dict[str, Any] | None = None
    defaults = {f.key: ([] if f.type in ("BIT", "IDV", "L16") else None)
                for f in schema if f.type != "EXI"}
    for token, param in iter_fields(ctx, where, block):
        f = find_field(schema, token)
        if f is None:
            ctx.warn(where, f"unrecognized exit field {token!r}")
            continue
        if f.type == "EXI":
            parts = param.strip().split(",", 1)
            if len(parts) != 2:
                ctx.warn(where, f"exit requires a direction and room: {param.strip()!r}")
                continue
            dnum, dname = lookup_dir(ctx, where, parts[0])
            to, raw = resolve_room(ctx, where, parts[1])
            cur = {"direction": dname, "direction_num": dnum, "to": to, "to_raw": raw}
            cur.update(defaults)
            exits.append(cur)
            continue
        if cur is None:
            ctx.warn(where, f"exit field {token!r} before any 'to'")
            continue
        cur[f.key] = parse_value(ctx, where, f, param)


def parse_pairs(ctx: Context, where: str, schema: Schema, block: str) -> list[dict[str, Any]]:
    """One block holding several records of the same sub-schema, e.g.
    ``extra { keywords{} desc{} keywords{} desc{} }``: a key that is already
    set starts a new record (roomdb.c case 6)."""
    out: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None
    for token, param in iter_fields(ctx, where, block):
        f = find_field(schema, token)
        if f is None:
            ctx.warn(where, f"unrecognized field {token!r}")
            continue
        if cur is None or f.key in cur:
            cur = {}
            out.append(cur)
        cur[f.key] = parse_value(ctx, where, f, param)
    return out


def parse_applies(ctx: Context, where: str, schema: Schema, block: str,
                  out: dict[str, Any]) -> None:
    """``apply { hitroll {1} damroll {2} ... }`` -> ``{"hitroll": 1, "damroll": 2}``.

    The server appends one (location, modifier) entry per line (objdb.c case
    49) and modifiers to the same location add up, so a repeated numeric apply
    is summed. Name-valued applies (spell_affect, resistance ...) hold a list
    and accumulate, since granting two spell affects is meaningful.
    """
    for token, param in iter_fields(ctx, where, block):
        f = find_field(schema, token)
        if f is None:
            ctx.warn(where, f"unrecognized apply {token!r}")
            continue
        v = parse_value(ctx, where, f, param)
        if f.type in ("E32", "E8", "ESTR"):
            out.setdefault(f.key, []).append(v)
        elif f.type in ("BIT", "IDV", "L16"):
            out.setdefault(f.key, [])
            out[f.key].extend(x for x in v if x not in out[f.key])
        elif f.key in out and out[f.key] is not None and v is not None:
            ctx.warn(where, f"apply {f.key!r} given twice; summing {out[f.key]} + {v}")
            out[f.key] += v
        else:
            out[f.key] = v


def parse_block(ctx: Context, where: str, schema: Schema, block: str, *, top: bool) -> dict[str, Any]:
    """Parse one brace block against ``schema``.

    Top-level records get every schema key (null when absent) so all rows of
    a JSONL file share one shape; nested blocks only carry what was written.
    """
    rec: dict[str, Any] = {}
    if top:
        seen_keys: set[str] = set()
        for f in schema:
            if f.key in seen_keys:
                continue
            seen_keys.add(f.key)
            if f.policy == "applies":
                rec[f.key] = {}
            else:
                rec[f.key] = [] if f.policy != "one" or f.type in ("BIT", "IDV", "L16", "SET", "ASTR") else None
    for token, param in iter_fields(ctx, where, block):
        f = find_field(schema, token)
        if f is None:
            ctx.warn(where, f"unrecognized {ctx.type_name or 'record'} field {token!r}")
            continue
        if f.policy == "exits":
            rec.setdefault(f.key, [])
            parse_exits(ctx, where, f.sub or (), param, rec[f.key])
            continue
        if f.policy == "list":
            rec.setdefault(f.key, [])
            rec[f.key].append(parse_value(ctx, where, f, param))
            continue
        if f.policy == "pairs":
            rec.setdefault(f.key, [])
            rec[f.key].extend(parse_pairs(ctx, where, f.sub or (), param))
            continue
        if f.policy == "applies":
            if not isinstance(rec.get(f.key), dict):
                rec[f.key] = {}
            parse_applies(ctx, where, f.sub or (), param, rec[f.key])
            continue
        if f.key in rec and rec[f.key] not in (None, []):
            ctx.warn(where, f"duplicate field {f.key!r}; keeping the last one")
        rec[f.key] = parse_value(ctx, where, f, param)
    return rec


# ---------------------------------------------------------------------------
# File driver (tran.c tran_file)
# ---------------------------------------------------------------------------

def read_block(lines: list[str], idx: int) -> tuple[str, int]:
    """tran.c ReadBlock: from line ``idx``, find ``{`` and return balanced contents.

    Returns (contents, index of the line after the closing brace).
    """
    text = "".join(lines[idx:])
    if text.find("{") < 0:
        raise ConvertError("missing '{' for block")
    contents, end = sub_block(text, 0)
    consumed = text[:end].count("\n")
    return contents, idx + consumed + 1


def _rel(ctx: Context, path: Path) -> str:
    try:
        return str(path.relative_to(ctx.root))
    except ValueError:
        return str(path)


def tran_file(ctx: Context, path: Path, schema: Schema, records: list[dict[str, Any]]) -> None:
    lines = read_text(path).splitlines(keepends=True)
    rel = _rel(ctx, path)
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip("\r\n")
        where = f"{rel}:{i + 1}"
        i += 1
        if not line.strip():
            continue
        if line.startswith("@"):
            name = line[1:].strip()
            try:
                body, i = read_block(lines, i)
            except ConvertError as e:
                raise ConvertError(f"{where}: nesting error on macro definition {name}: {e}") from None
            ctx.macros[name] = body
            continue
        if line.startswith("#"):
            body = line[1:].strip()
            if not body:
                continue
            word, _, rest = body.partition(" ")
            rest = rest.strip()
            if word == "include":
                name = rest.strip('<>"').strip()
                inc = path.parent / name
                if not inc.exists():
                    raise ConvertError(f"{where}: cannot open include {name!r}")
                tran_file(ctx, inc, schema, records)
            elif word == "offset":
                if re.fullmatch(r"\d+", rest):
                    ctx.offset = int(rest)
                    ctx.offset_name = None
                else:
                    if rest not in ctx.defines:
                        ctx.warn(where, f"#offset {rest!r} is not defined; using 0")
                    ctx.offset = ctx.defines.get(rest, 0)
                    ctx.offset_name = rest
            elif word == "define":
                # tran: name runs to the first space or '=', value is atoi()
                m = re.match(r"([^\s=]+)\s*=?\s*([+-]?\d+)", rest)
                if not m:
                    ctx.warn(where, f"bad #define {rest!r}")
                    continue
                name, value = m.group(1), int(m.group(2))
                # var_insert rejects a duplicate *value*, not a duplicate name;
                # var_lookup then returns the lowest value for a name.
                if value in ctx.defines.values():
                    raise ConvertError(f"{where}: duplicate identifier {name!r} (value {value} already defined)")
                if name in ctx.defines:
                    ctx.warn(where, f"{name!r} defined twice; tran resolves it to {min(value, ctx.defines[name])}")
                    value = min(value, ctx.defines[name])
                ctx.defines[name] = value
            # any other '#' line is a comment, as in tran
            continue
        if not line[0].isdigit():
            # tran ignores lines it does not recognise (comments, ';' notes ...)
            continue

        local = int(re.match(r"\d+", line).group())
        vnum = local + ctx.offset
        try:
            block, i = read_block(lines, i)
        except ConvertError as e:
            raise ConvertError(f"{where}: nesting error: {e}") from None
        if "@" in block:
            block = macro_expand(ctx, where, block)
        if vnum in ctx.seen_vnums:
            ctx.warn(where, f"duplicate vnum {vnum} (first seen at {ctx.seen_vnums[vnum]})")
        else:
            ctx.seen_vnums[vnum] = where

        rec: dict[str, Any] = {"vnum": vnum}
        if ctx.type_name == "rooms":
            rec["area"] = ctx.offset_name
            rec["local_number"] = local
        rec["source"] = where
        rec.update(parse_block(ctx, where, schema, block, top=True))
        records.append(rec)


def convert(ctx: Context, entry: Path, schema: Schema) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tran_file(ctx, entry, schema, records)
    return records
