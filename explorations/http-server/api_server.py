"""
api_server — the non-game HTTP side for perilousrealms.com.

Exploration sketch, not deployed. Caddy routes /api/* here (localhost:8000).
The game text itself goes over /ws, which is the tty proxy; it is mounted
here too so a single uvicorn process can serve both if wanted (then point
Caddy's /ws at :8000 instead of :7681).

Run:   uvicorn api_server:app --host 127.0.0.1 --port 8000
Env:   PR_IMAGES  directory of room pictures (default ./images)
       PR_GAME_HOST / PR_GAME_PORT   passed through to the tty proxy

Pictures are plain files:
    images/rooms/<vnum>.webp           one specific room (vnum is global)
    images/zones/<zone>.webp           the zone
The page asks for the room picture and, on 404, the zone picture.
"""

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

import tty_proxy

IMAGES = Path(os.environ.get("PR_IMAGES", "images"))
SAFE = re.compile(r"^[A-Za-z0-9_\-]+$")   # zone names as used in world/ROOM

app = FastAPI(title="Perilous Realms web")
app.mount("/ws", tty_proxy.app)           # /ws -> the relay in tty_proxy.py


def _safe(name: str) -> str:
    if not SAFE.match(name):
        raise HTTPException(400, "bad name")
    return name


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


def _picture(p: Path):
    if not p.is_file():
        raise HTTPException(404, "no picture")
    return FileResponse(p, media_type="image/webp",
                        headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/room-image/{vnum}")
def room_image(vnum: int):
    return _picture(IMAGES / "rooms" / f"{vnum}.webp")


@app.get("/api/zone-image/{zone}")
def zone_image(zone: str):
    return _picture(IMAGES / "zones" / f"{_safe(zone)}.webp")


# Later, as wanted: /api/online (the game already writes an online-status
# HTML file from comm.c; read or replace it), /api/motd, /api/news, and the
# landing page's dynamic bits. The React build itself is served by Caddy.
