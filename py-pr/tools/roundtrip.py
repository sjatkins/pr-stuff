"""Prove the JSONL and the models are coherent: for every line of every
py_json/out/*.jsonl, validate -> dump -> validate -> dump must be the
identity, and the first dump must equal the line itself (the file is
canonical). Exit 1 on any difference.

Run from py-pr:  .venv/bin/python tools/roundtrip.py [out_dir]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classes import JSONL_MODELS  # noqa: E402


def dump(m) -> dict:
    return json.loads(m.model_dump_json(by_alias=True, exclude_unset=True))


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "py_json" / "out")
    status = 0
    for name, model in JSONL_MODELS.items():
        path = out / f"{name}.jsonl"
        if not path.exists():
            print(f"{name:12s} missing {path.name}")
            continue
        n = not_canonical = unstable = no_id = 0
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                n += 1
                rec = json.loads(line)
                m1 = model.model_validate(rec)
                d1 = dump(m1)
                if d1 != rec:
                    not_canonical += 1
                d2 = dump(model.model_validate(d1))
                if d2 != d1:
                    unstable += 1
                if not m1.id:
                    no_id += 1
        ok = not (not_canonical or unstable or no_id)
        status |= 0 if ok else 1
        print(f"{name:12s} {n:6d} records  {'ok' if ok else f'NOT canonical: {not_canonical}, unstable: {unstable}, no id: {no_id}'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
