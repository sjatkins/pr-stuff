"""Validate every py_json/out/*.jsonl line against its pydantic model.

Run from py-pr:  uv run python tools/validate_jsonl.py [out_dir]
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pydantic import ValidationError  # noqa: E402

from classes import JSONL_MODELS  # noqa: E402


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2] / "py_json" / "out")
    bad_total = 0
    for name, model in JSONL_MODELS.items():
        path = out / f"{name}.jsonl"
        if not path.exists():
            print(f"{name:10s} missing {path}")
            continue
        n = 0
        errors: Counter[str] = Counter()
        first: dict[str, str] = {}
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                n += 1
                try:
                    model.model_validate(json.loads(line))
                except ValidationError as e:
                    for err in e.errors():
                        key = f"{'.'.join(str(p) for p in err['loc'])}: {err['type']}"
                        errors[key] += 1
                        first.setdefault(key, str(err.get("input"))[:80])
        bad = sum(errors.values())
        bad_total += bad
        print(f"{name:10s} {n:6d} records  {'OK' if not bad else f'{bad} errors'}")
        for key, c in errors.most_common(8):
            print(f"    {c:6d}  {key}   e.g. {first[key]}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    sys.exit(main())
