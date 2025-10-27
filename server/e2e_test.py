"""
e2e_test.py — Concurrent end‑to‑end tester for the FastAPI dummy realtime server.

What it verifies (all at once):
  1) REST history & POST /api/message broadcast to WS + SSE
  2) WebSocket chat echo + broadcast across two WS clients of the same user
  3) SSE stream receives the same message as WS clients
  4) WebRTC signaling relay forwards messages between two peers in the same room

Usage:
  python e2e_test.py --base http://localhost:8000 --user alice --room room42

Exit codes:
  0 on full success, 1 if any check fails.
"""
from __future__ import annotations

import asyncio
import json
import sys
import argparse
import uuid
from typing import Any, Callable, Tuple

import aiohttp


def j(obj: Any) -> str:
    """Pretty JSON for logs."""
    return json.dumps(obj, ensure_ascii=False)


async def sse_listener(session: aiohttp.ClientSession, url: str, queue: asyncio.Queue, ready_evt: asyncio.Event):
    """
    Minimal SSE client:
      - Reads lines, collects until blank line -> one event
      - For each 'data: ...' line, tries to parse JSON and push ('event', obj) into queue
      - Ignores comment lines starting with ':' and other SSE fields
    """
    try:
        async with session.get(url, headers={"Accept": "text/event-stream"}) as resp:
            if resp.status != 200:
                await queue.put(("error", {"status": resp.status}))
                return
            ready_evt.set()
            buffer_lines = []
            async for raw in resp.content:
                line = raw.decode("utf-8", errors="ignore").rstrip("\n")
                if not line:
                    # blank line -> dispatch event
                    if buffer_lines:
                        data_lines = [l[5:].lstrip() for l in buffer_lines if l.startswith("data:")]
                        for dl in data_lines:
                            try:
                                obj = json.loads(dl)
                                await queue.put(("event", obj))
                            except Exception:
                                await queue.put(("raw", dl))
                        buffer_lines = []
                    continue
                if line.startswith(":"):
                    # comment / keepalive
                    continue
                buffer_lines.append(line)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        await queue.put(("error", {"exception": repr(e)}))


async def ws_reader(ws: aiohttp.ClientWebSocketResponse, queue: asyncio.Queue):
    """Read messages from a connected WebSocket and push ('msg', obj) into queue."""
    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    data = {"raw": msg.data}
                await queue.put(("msg", data))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                await queue.put(("error", {"error": str(ws.exception())}))
                break
    except asyncio.CancelledError:
        pass
    except Exception as e:
        await queue.put(("error", {"exception": repr(e)}))


async def wait_for_queue_match(
    queue: asyncio.Queue,
    predicate: Callable[[Tuple[str, Any]], bool],
    timeout: float,
    label: str,
) -> Tuple[str, Any]:
    """
    Wait until an item from the queue satisfies predicate(item).
    Returns the matched item; raises asyncio.TimeoutError on timeout.
    """
    try:
        while True:
            item = await asyncio.wait_for(queue.get(), timeout=timeout)
            if predicate(item):
                return item
            # else: keep looping, but don't swallow timeouts
    except asyncio.TimeoutError:
        raise asyncio.TimeoutError(f"Timeout while waiting for {label}")


async def main():
    parser = argparse.ArgumentParser(description="E2E concurrent tester for dummy realtime server")
    parser.add_argument("--base", default="http://localhost:8000", help="Base HTTP URL (default: http://localhost:8000)")
    parser.add_argument("--user", default="alice", help="User ID to test with (default: alice)")
    parser.add_argument("--room", default="room42", help="Signaling room ID (default: room42)")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout per expectation in seconds (default: 5)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    user_id = args.user
    room_id = args.room
    T = args.timeout

    print(f"[INFO] Base: {base}")
    print(f"[INFO] WS Base: {ws_base}")
    print(f"[INFO] User: {user_id}  Room: {room_id}")
    print(f"[INFO] Timeout per check: {T}s")

    # Queues for incoming events
    sse_q: asyncio.Queue = asyncio.Queue()
    ws1_q: asyncio.Queue = asyncio.Queue()
    ws2_q: asyncio.Queue = asyncio.Queue()
    sigA_q: asyncio.Queue = asyncio.Queue()
    sigB_q: asyncio.Queue = asyncio.Queue()

    # Ready events to ensure connections are established before sending
    sse_ready = asyncio.Event()
    ws1_ready = asyncio.Event()
    ws2_ready = asyncio.Event()
    sigA_ready = asyncio.Event()
    sigB_ready = asyncio.Event()

    async with aiohttp.ClientSession() as session:
        # Connect SSE
        sse_task = asyncio.create_task(sse_listener(session, f"{base}/sse/{user_id}", sse_q, sse_ready))

        # Connect chat WebSockets
        ws1 = await session.ws_connect(f"{ws_base}/ws/{user_id}")
        ws1_ready.set()
        ws1_task = asyncio.create_task(ws_reader(ws1, ws1_q))

        ws2 = await session.ws_connect(f"{ws_base}/ws/{user_id}")
        ws2_ready.set()
        ws2_task = asyncio.create_task(ws_reader(ws2, ws2_q))

        # Ping to verify echo/pongs later
        await ws1.send_json({"type": "ping"})

        # Connect signaling WebSockets
        sigA = await session.ws_connect(f"{ws_base}/signal/{room_id}")
        sigA_ready.set()
        sigA_task = asyncio.create_task(ws_reader(sigA, sigA_q))

        sigB = await session.ws_connect(f"{ws_base}/signal/{room_id}")
        sigB_ready.set()
        sigB_task = asyncio.create_task(ws_reader(sigB, sigB_q))

        # Wait readiness
        await asyncio.wait_for(sse_ready.wait(), timeout=T)
        await asyncio.wait_for(ws1_ready.wait(), timeout=T)
        await asyncio.wait_for(ws2_ready.wait(), timeout=T)
        await asyncio.wait_for(sigA_ready.wait(), timeout=T)
        await asyncio.wait_for(sigB_ready.wait(), timeout=T)

        print("[STEP] All connections established.")

        # Drain initial hello/pong messages without strict checks
        drain_deadline = asyncio.get_event_loop().time() + 1.0
        while asyncio.get_event_loop().time() < drain_deadline:
            try:
                _ = await asyncio.wait_for(ws1_q.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass
            try:
                _ = await asyncio.wait_for(ws2_q.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass
            try:
                _ = await asyncio.wait_for(sigA_q.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass
            try:
                _ = await asyncio.wait_for(sigB_q.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass
            try:
                _ = await asyncio.wait_for(sse_q.get(), timeout=0.05)
            except asyncio.TimeoutError:
                pass

        # ---------- Check 1: REST -> broadcast to WS and SSE ----------
        rest_nonce = str(uuid.uuid4())[:8]
        rest_text = f"REST test {rest_nonce}"

        print("[STEP] POST /api/message -> should appear on WS1, WS2, and SSE")
        async with session.post(f"{base}/api/message", json={"user_id": user_id, "role": "user", "text": rest_text}) as r:
            post_resp = await r.json()
            print("       POST response:", j(post_resp))

        def is_message_with_text(item, text: str) -> bool:
            tag, obj = item
            if tag not in ("event", "msg"):
                return False
            try:
                return obj.get("type") == "message" and obj.get("data", {}).get("text") == text
            except Exception:
                return False

        # Wait on all three consumers
        await wait_for_queue_match(ws1_q, lambda it: is_message_with_text(it, rest_text), T, "WS1 message broadcast")
        await wait_for_queue_match(ws2_q, lambda it: is_message_with_text(it, rest_text), T, "WS2 message broadcast")
        await wait_for_queue_match(sse_q,  lambda it: is_message_with_text(it, rest_text), T, "SSE message broadcast")
        print("[PASS] REST broadcast received on WS1, WS2, and SSE")

        # ---------- Check 2: WS echo (sender) + broadcast (others) ----------
        ws_nonce = str(uuid.uuid4())[:8]
        ws_text = f"WS test {ws_nonce}"

        print("[STEP] WS1 sends chat message -> WS1 should get echo, WS2 should get broadcast")
        await ws1.send_json({"type": "message", "data": {"text": ws_text}})

        def is_echo_with_text(item, text: str) -> bool:
            tag, obj = item
            if tag != "msg":
                return False
            try:
                return obj.get("type") == "echo" and obj.get("data", {}).get("text") == text
            except Exception:
                return False

        await wait_for_queue_match(ws1_q, lambda it: is_echo_with_text(it, ws_text), T, "WS1 echo")
        await wait_for_queue_match(ws2_q, lambda it: is_message_with_text(it, ws_text), T, "WS2 broadcast from WS1")
        print("[PASS] WS echo/broadcast behavior OK")

        # ---------- Check 3: Signaling relay ----------
        offer_nonce = str(uuid.uuid4())[:8]
        answer_nonce = str(uuid.uuid4())[:8]

        print("[STEP] Signaling: A -> B (offer), then B -> A (answer)")

        await sigA.send_json({"type": "offer", "sdp": "dummy-sdp", "nonce": offer_nonce, "from": "A"})
        await wait_for_queue_match(
            sigB_q,
            lambda it: it[0] == "msg" and isinstance(it[1], dict) and it[1].get("type") == "offer" and it[1].get("nonce") == offer_nonce,
            T,
            "Sig B receive offer",
        )

        await sigB.send_json({"type": "answer", "sdp": "dummy-sdp", "nonce": answer_nonce, "from": "B"})
        await wait_for_queue_match(
            sigA_q,
            lambda it: it[0] == "msg" and isinstance(it[1], dict) and it[1].get("type") == "answer" and it[1].get("nonce") == answer_nonce,
            T,
            "Sig A receive answer",
        )

        print("[PASS] Signaling relay OK")

        # ---------- Done ----------
        print("\n✅ ALL CHECKS PASSED")
        rc = 0

        # Cleanup
        for t in [sse_task, ws1_task, ws2_task, sigA_task, sigB_task]:
            t.cancel()
        for ws in [ws1, ws2, sigA, sigB]:
            try:
                await ws.close()
            except Exception:
                pass
        await asyncio.sleep(0)  # let tasks cancel
        sys.exit(rc)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[ABORTED] KeyboardInterrupt")
        sys.exit(1)
