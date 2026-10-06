"""Canonical record shape: the py-pr pydantic model's own JSON.

py_json has no hard dependency on pydantic. When ../py-pr is present (or the
``classes`` module is importable), ``canonical_records`` validates each
extracted dict against its model and writes back ``model_dump`` with
``by_alias`` and ``exclude_unset``, so that loading the JSONL with the model
and dumping it again is the identity.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_PY_PR = Path(__file__).resolve().parents[3] / "py-pr"
for cand in (_PY_PR / "src",):
    if cand.is_dir() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))
# a py-pr virtualenv, if present, supplies pydantic when the running
# interpreter has none
_venv = _PY_PR / ".venv" / "lib"
if _venv.is_dir():
    for sp in sorted(_venv.glob("python*/site-packages")):
        if str(sp) not in sys.path:
            sys.path.append(str(sp))

from classes import JSONL_MODELS  # noqa: E402  (py-pr/src/classes.py)


def canonical_records(type_name: str, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    model = JSONL_MODELS.get(type_name)
    if model is None:
        return records, [f"no py-pr model for {type_name}; wrote raw records"]
    out = []
    for rec in records:
        m = model.model_validate(rec)
        out.append(json.loads(m.model_dump_json(by_alias=True, exclude_unset=True)))
    return out, []
