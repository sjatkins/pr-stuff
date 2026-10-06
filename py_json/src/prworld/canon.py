"""Canonical record shape: the pr-be pydantic model's own JSON.

py_json has no hard dependency on pydantic. When ../pr-be is present (or
``pr_be.classes`` is importable), ``canonical_records`` validates each
extracted dict against its model and writes back ``model_dump`` with
``by_alias`` and ``exclude_unset``, so that loading the JSONL with the model
and dumping it again is the identity. Records get their ``id`` here, once:
a record that already carries one keeps it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_PR_BE = Path(__file__).resolve().parents[3] / "pr-be"
for cand in (_PR_BE / "src",):
    if cand.is_dir() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))
# pr-be's virtualenv, if present, supplies pydantic and sjasoft-utils when
# the running interpreter has them not
_venv = _PR_BE / ".venv" / "lib"
if _venv.is_dir():
    for sp in sorted(_venv.glob("python*/site-packages")):
        if str(sp) not in sys.path:
            sys.path.append(str(sp))

from pr_be.classes import JSONL_MODELS  # noqa: E402  (pr-be/src/pr_be/classes.py)


def canonical_records(type_name: str, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    model = JSONL_MODELS.get(type_name)
    if model is None:
        return records, [f"no pr-be model for {type_name}; wrote raw records"]
    out = []
    for rec in records:
        m = model.model_validate(rec)
        out.append(json.loads(m.model_dump_json(by_alias=True, exclude_unset=True)))
    return out, []
