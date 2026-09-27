"""Convert the Perilous Realms room sources (world/ROOM) to JSONL.

Thin wrapper kept for the ``rooms`` command; the parser lives in the
``prworld`` package (``prworld.tranparse`` driven by ``prworld.schemas``),
which also handles mobs, objects, shops, races, sectors, clans, item sets,
effects, skills, zones and classes via the ``world2jsonl`` command.
"""

from __future__ import annotations

import sys

from .cli import rooms_main as main

if __name__ == "__main__":
    sys.exit(main())
