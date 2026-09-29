# Web front end for Perilous Realms — the working pieces

Exploration only. Nothing here is deployed or wired up. Production today
(checked 2026-09-28 as user `pr`) has the game on 0.0.0.0:2150 and :5024,
nothing on 80/443, and no Caddy service active.

## Pieces

| piece | what it does | listens on | state |
|---|---|---|---|
| Caddy | TLS for perilousrealms.com, routes `/ws`, `/api/*`, static SPA | 80, 443 | `Caddyfile` here |
| tty proxy | dumb websocket <-> TCP relay to the game | localhost:7681 | `tty_proxy.py` sketch (FastAPI websocket + asyncio) |
| FastAPI | `/api/room-image/{vnum}`, `/api/zone-image/{zone}`; mounts the tty proxy at `/ws`; later non-game pages | localhost:8000 | `api_server.py` sketch |
| React build | landing page; game page = picture widget + xterm.js terminal widget sharing one websocket | static files | `web/` sketch (Vite + React) |
| pr3 | unchanged, plus `-a 2151` web port; small C change to skip telnet negotiation and emit an OSC room marker on that port | localhost:2151 | not written |

The tty proxy can live inside the FastAPI process as a `/ws` endpoint
(then the Caddyfile's `/ws` block points at :8000 too), or be a separate
process. Separate keeps the game relay trivially restartable without
touching the API.

## Room marker

On web-port connections `look_room` (`src/look.c`) appends
`ESC ] 9001 ; room=<zone>:<vnum> BEL` (OSC needs a numeric selector; 9001 is unused by terminals). xterm.js in the browser registers an OSC
handler for it, hides it, and tells the picture widget to fetch
`/api/room-image/<vnum>`, falling back to `/api/zone-image/<zone>` on 404. The proxy never parses game text.

## Docker later

Caddy, tty proxy and FastAPI can each be a container on one compose network;
then `localhost:7681` / `localhost:8000` in the Caddyfile become the service
names (`ttyproxy:7681`, `api:8000`), and the game port is reached via
`host.docker.internal:2151` or by running the game container on the same
network. The Caddyfile is the only file that changes between the two layouts.
On a dev machine the same compose file runs against the local `live/` game
with a self-signed or `localhost` certificate (Caddy does that automatically
for `localhost`).

## Dev loop

```
cd explorations/http-server
pip install -r requirements.txt
uvicorn tty_proxy:app --port 7681 &      # or api_server:app alone on 8000
uvicorn api_server:app --port 8000 &
cd web && npm install && npm run dev     # http://localhost:5173, proxies /api and /ws
```

`npm run build` produces `web/dist/`, which is what Caddy's `root` points at.
