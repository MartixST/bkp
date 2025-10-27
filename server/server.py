from __future__ import annotations

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse

# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def utc_iso() -> str:
    # Return current UTC timestamp as string
    return datetime.now(timezone.utc).isoformat()

# -----------------------------------------------------------------------------
# In-memory stores
# -----------------------------------------------------------------------------

MESSAGES: Dict[str, List[Dict[str, Any]]] = defaultdict(list)  # user_id -> list of messages

class Hub:
    # Tracks all realtime connections and provides broadcast helpers
    def __init__(self) -> None:
        self.ws_by_user: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.ws_rooms: Dict[str, Set[WebSocket]] = defaultdict(set)

        self.sse_queues: Dict[str, List[asyncio.Queue]] = defaultdict(list)

        self._lock = asyncio.Lock()

    # ---------------------- WebSocket (chat) ----------------------

    async def add_ws_user(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.ws_by_user[user_id].add(ws)

    async def remove_ws_user(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.ws_by_user[user_id].discard(ws)
            if not self.ws_by_user[user_id]:
                self.ws_by_user.pop(user_id, None)

    async def broadcast_to_user(self, user_id: str, payload: Dict[str, Any]) -> None:
        # Send payload to all WebSockets and SSE subscribers of a user
        for ws in list(self.ws_by_user.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                await self.remove_ws_user(user_id, ws)

        for q in list(self.sse_queues.get(user_id, [])):
            try:
                q.put_nowait(payload)
            except Exception:
                pass

    # ---------------------- WebRTC signaling ----------------------

    async def add_ws_room(self, room_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.ws_rooms[room_id].add(ws)

    async def remove_ws_room(self, room_id: str, ws: WebSocket) -> None:
        async with self._lock:
            self.ws_rooms[room_id].discard(ws)
            if not self.ws_rooms[room_id]:
                self.ws_rooms.pop(room_id, None)

    async def broadcast_room(self, room_id: str, payload: Dict[str, Any], sender: WebSocket) -> None:
        # Relay signaling messages to everyone except the sender
        for ws in list(self.ws_rooms.get(room_id, [])):
            if ws is sender:
                continue
            try:
                await ws.send_text(json.dumps(payload, ensure_ascii=False))
            except Exception:
                await self.remove_ws_room(room_id, ws)

hub = Hub()

# -----------------------------------------------------------------------------
# FastAPI app
# -----------------------------------------------------------------------------

app = FastAPI(title="Dummy Realtime Server for React Chat Bot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Health / basic routes
# -----------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"ok": True, "service": "dummy-realtime", "time": utc_iso()}

# -----------------------------------------------------------------------------
# REST endpoints
# -----------------------------------------------------------------------------

@app.get("/api/history/{user_id}")
async def get_history(user_id: str):
    return {"user_id": user_id, "messages": MESSAGES.get(user_id, [])[-200:]}

@app.post("/api/message")
async def post_message(payload: Dict[str, Any]):
    user_id = str(payload.get("user_id", "")).strip()
    text = str(payload.get("text", "")).strip()
    role = (payload.get("role") or "user").strip()

    if not user_id or not text:
        raise HTTPException(status_code=400, detail="user_id and text are required")

    msg = {
        "id": str(uuid.uuid4()),
        "ts": utc_iso(),
        "user_id": user_id,
        "role": role,
        "text": text,
    }
    MESSAGES[user_id].append(msg)

    await hub.broadcast_to_user(user_id, {"type": "message", "data": msg})
    return {"ok": True, "message": msg}

# -----------------------------------------------------------------------------
# SSE endpoint
# -----------------------------------------------------------------------------

@app.get("/sse/{user_id}")
async def sse(user_id: str, request: Request):
    q: asyncio.Queue = asyncio.Queue()
    hub.sse_queues[user_id].append(q)

    async def event_gen():
        # Send a "hello" event
        await q.put({"type": "sse_hello", "data": {"ts": utc_iso(), "note": "connected"}})

        try:
            while True:
                # If no data within 25s, send a keepalive comment
                try:
                    item = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f": keepalive {utc_iso()}\n\n"

                if await request.is_disconnected():
                    break
        finally:
            try:
                hub.sse_queues[user_id].remove(q)
            except ValueError:
                pass

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_gen(), media_type="text/event-stream", headers=headers)

# -----------------------------------------------------------------------------
# WebSocket (chat) endpoint
# -----------------------------------------------------------------------------

@app.websocket("/ws/{user_id}")
async def ws_chat(websocket: WebSocket, user_id: str):
    await websocket.accept()
    await hub.add_ws_user(user_id, websocket)

    # Send a greeting
    await websocket.send_text(json.dumps({"type": "ws_hello", "data": {"ts": utc_iso(), "user_id": user_id}}))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                msg = {"type": "text", "data": {"text": raw}}

            mtype = msg.get("type")

            if mtype == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "ts": utc_iso()}))
                continue

            if mtype == "message":
                # Echo back
                await websocket.send_text(json.dumps({"type": "echo", "data": msg.get("data")}, ensure_ascii=False))
                # Also broadcast to the same user's channels
                await hub.broadcast_to_user(user_id, {"type": "message", "data": {**(msg.get("data") or {}), "echoed": True, "ts": utc_iso()}})
                continue

            # Unknown message type -> acknowledge anyway
            await websocket.send_text(json.dumps({"type": "ack", "data": msg, "ts": utc_iso()}, ensure_ascii=False))

    except WebSocketDisconnect:
        # Client closed connection
        await hub.remove_ws_user(user_id, websocket)
    except Exception as e:
        await hub.remove_ws_user(user_id, websocket)
        # Optionally log in real world
        await asyncio.sleep(0)  # yield to event loop

# -----------------------------------------------------------------------------
# Minimal WebRTC signaling via WebSocket
# -----------------------------------------------------------------------------

@app.websocket("/signal/{room_id}")
async def ws_signal(websocket: WebSocket, room_id: str):
    await websocket.accept()
    await hub.add_ws_room(room_id, websocket)
    await websocket.send_text(json.dumps({"type": "signal_hello", "room": room_id, "ts": utc_iso()}))

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"type": "raw", "data": raw}

            payload.setdefault("ts", utc_iso())
            await hub.broadcast_room(room_id, payload, sender=websocket)

    except WebSocketDisconnect:
        await hub.remove_ws_room(room_id, websocket)
    except Exception:
        await hub.remove_ws_room(room_id, websocket)
        await asyncio.sleep(0)

# -----------------------------------------------------------------------------
# Сlear everything
# -----------------------------------------------------------------------------

@app.post("/__dev__/reset")
async def dev_reset():
    # Clear messages
    MESSAGES.clear()
    return {"ok": True, "reset_at": utc_iso()}
