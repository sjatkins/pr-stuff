"""
tty_proxy — websocket <-> TCP relay between a browser and pr3.

Exploration sketch, not deployed. One browser websocket = one TCP
connection to the game's web port. Bytes are relayed unchanged in both
directions; the game does its own login, echo control and colour, and the
OSC room marker it emits passes straight through to xterm.js.

Run:   uvicorn tty_proxy:app --host 127.0.0.1 --port 7681
Env:   PR_GAME_HOST (default 127.0.0.1), PR_GAME_PORT (default 2151)

Caddy routes /ws here. The same `app` can be mounted inside the FastAPI
server instead of running alone; nothing here depends on being separate.
"""

import asyncio
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

GAME_HOST = os.environ.get("PR_GAME_HOST", "127.0.0.1")
GAME_PORT = int(os.environ.get("PR_GAME_PORT", "2151"))

# The game sends IAC DO LINEMODE on connect. If the game's web-port change
# (skip telnet negotiation) is not in yet, strip IAC sequences here so the
# terminal never sees them. Harmless once the game stops sending them.
IAC, SB, SE = 255, 250, 240


def strip_telnet(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b != IAC:
            out.append(b)
            i += 1
        elif i + 1 < len(data) and data[i + 1] == IAC:   # escaped 0xff
            out.append(IAC)
            i += 2
        elif i + 1 < len(data) and data[i + 1] == SB:    # subnegotiation
            j = data.find(bytes([IAC, SE]), i + 2)
            i = len(data) if j < 0 else j + 2
        else:                                            # IAC cmd opt
            i += 3
    return bytes(out)


app = FastAPI()


@app.websocket("/ws")
async def ws_to_game(ws: WebSocket) -> None:
    await ws.accept()
    try:
        reader, writer = await asyncio.open_connection(GAME_HOST, GAME_PORT)
    except OSError:
        await ws.close(code=1013, reason="game not available")
        return

    async def game_to_browser() -> None:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            await ws.send_bytes(strip_telnet(data))

    async def browser_to_game() -> None:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            payload = msg.get("bytes")
            if payload is None:
                payload = msg.get("text", "").encode("latin-1", "replace")
            writer.write(payload)
            await writer.drain()

    tasks = [asyncio.create_task(game_to_browser()),
             asyncio.create_task(browser_to_game())]
    try:
        # Whichever side hangs up first ends the session.
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for t in tasks:
            t.cancel()
        writer.close()
        try:
            await ws.close()
        except Exception:
            pass
