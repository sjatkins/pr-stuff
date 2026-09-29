"""
api_server — the non-game HTTP side for perilousrealms.com.

Exploration sketch, not deployed. Caddy routes /api/* here (localhost:8000).
The game text itself goes over /ws, which is the tty proxy; it is mounted
here too so a single uvicorn process can serve both if wanted (then point
Caddy's /ws at :8000 instead of :7681).

Run:   uvicorn api_server:app --host 127.0.0.1 --port 8000
Env:   PR_IMAGES  directory of room pictures (default ./images)
       PR_GAME_HOST / PR_GAME_PORT   passed through to the tty proxy

Pictures are plain files, filled in over time in any order:
    images/rooms/<zone>/<num>.webp     one specific room
    images/zones/<zone>.webp           any room in that zone
    images/sectors/<sector>.webp       any room of that sector type
    images/default.webp                anything else
The browser asks for one room and gets the most specific picture that
exists. Nothing in the game needs to know which pictures exist.
"""

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse

import tty_proxy

IMAGES = Path(os.environ.get("PR_IMAGES", "images"))
SAFE = re.compile(r"^[A-Za-z0-9_\-]+$")   # zone/sector names as used in world/ROOM

app = FastAPI(title="Perilous Realms web")
app.mount("/ws", tty_proxy.app)           # /ws -> the relay in tty_proxy.py


def _safe(name: str) -> str:
    if not SAFE.match(name):
        raise HTTPException(400, "bad name")
    return name


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.get("/api/room-image/{zone}/{num}")
def room_image(zone: str, num: int, sector: str | None = None):
    """Most specific picture for a room; the page passes sector from the
    game's OSC marker so the API needs no world data of its own."""
    zone = _safe(zone)
    candidates = [
        IMAGES / "rooms" / zone / f"{num}.webp",
        IMAGES / "zones" / f"{zone}.webp",
    ]
    if sector:
        candidates.append(IMAGES / "sectors" / f"{_safe(sector)}.webp")
    candidates.append(IMAGES / "default.webp")
    for p in candidates:
        if p.is_file():
            return FileResponse(p, media_type="image/webp",
                                headers={"Cache-Control": "public, max-age=3600"})
    raise HTTPException(404, "no picture")


@app.get("/api/room-image/{zone}/{num}/tier")
def room_image_tier(zone: str, num: int, sector: str | None = None) -> JSONResponse:
    """Which tier would answer; handy for the page and for filling gaps."""
    zone = _safe(zone)
    if (IMAGES / "rooms" / zone / f"{num}.webp").is_file():
        tier = "room"
    elif (IMAGES / "zones" / f"{zone}.webp").is_file():
        tier = "zone"
    elif sector and (IMAGES / "sectors" / f"{_safe(sector)}.webp").is_file():
        tier = "sector"
    elif (IMAGES / "default.webp").is_file():
        tier = "default"
    else:
        tier = None
    return JSONResponse({"zone": zone, "num": num, "sector": sector, "tier": tier})


# Later, as wanted: /api/online (the game already writes an online-status
# HTML file from comm.c; read or replace it), /api/motd, /api/news, and the
# landing page's dynamic bits. The React build itself is served by Caddy.
