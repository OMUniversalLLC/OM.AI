#!/usr/bin/env python3
"""OM AI local counter-to-speaker event bridge (no footage or face recognition).

Receives occupancy counts from AN ALREADY CONFIGURED on-premises camera analytics system.
No computer vision model, RTSP reader or cloud video upload is included.
Run on a secured store LAN, with an event-auth token and optional Home Assistant TTS.
"""
from __future__ import annotations

import datetime as dt
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.request import Request, urlopen


def float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class CounterMonitor:
    def __init__(self, wait_seconds: float = 25, cooldown_seconds: float = 120, min_samples: int = 2):
        self.wait_seconds = wait_seconds
        self.cooldown_seconds = cooldown_seconds
        self.min_samples = min_samples
        self.state: dict[str, dict] = {}
        self.lock = Lock()

    def evaluate(self, key: str, customers: int, staff: int, now: float) -> dict:
        if customers < 0 or staff < 0 or customers > 100 or staff > 100:
            raise ValueError("Invalid occupancy count")
        with self.lock:
            current = self.state.setdefault(key, {"waiting_since": None, "last_alert": -1e12, "samples": 0})
            if customers == 0 or staff > 0:
                current["waiting_since"] = None
                current["samples"] = 0
                return {"state": "clear_or_attended", "should_alert": False}
            if current["waiting_since"] is None:
                current["waiting_since"] = now
            current["samples"] += 1
            elapsed = max(0, now - current["waiting_since"])
            if (elapsed >= self.wait_seconds and current["samples"] >= self.min_samples
                    and now - current["last_alert"] >= self.cooldown_seconds):
                current["last_alert"] = now
                return {"state": "waiting_unattended", "should_alert": True, "elapsed": round(elapsed)}
            return {"state": "observing", "should_alert": False, "elapsed": round(elapsed)}


def speak_homeassistant(message: str) -> dict:
    """Home Assistant REST TTS: uses the /api/services/tts/speak endpoint.

    Configure *valid* Home Assistant TTS entity and speaker entity. None are assumed.
    Speaker is not driven if any value is absent. Avoid announcing personal details.
    """
    base = os.getenv("HA_URL", "").rstrip("/")
    token = os.getenv("HA_TOKEN", "")
    tts_entity = os.getenv("HA_TTS_ENTITY", "")
    speaker = os.getenv("HA_MEDIA_PLAYER", "")
    if not all([base, token, tts_entity, speaker]):
        return {"delivered": False, "reason": "Speaker not configured"}
    if not base.startswith("https://") and not (
            base.startswith("http://127.0.0.1:") or base.startswith("http://localhost:")):
        return {"delivered": False, "reason": "Use HTTPS Home Assistant URL or localhost"}
    payload = json.dumps({"entity_id": tts_entity, "media_player_entity_id": speaker,
                          "message": message}).encode("utf-8")
    request = Request(f"{base}/api/services/tts/speak", data=payload, method="POST",
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=5) as result:
            return {"delivered": 200 <= result.status < 300, "status": result.status}
    except Exception:
        return {"delivered": False, "reason": "Speaker endpoint unavailable"}


MONITOR = CounterMonitor(wait_seconds=float_env("OM_WAIT_SECONDS", 25),
                         cooldown_seconds=float_env("OM_ALERT_COOLDOWN", 120))
TOKEN = os.getenv("OM_EDGE_TOKEN", "")


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/health":
            return self.respond(404, {"error": "not found"})
        return self.respond(200, {"service": "om-ai-counter-alert", "status": "listening_for_occupancy_events",
                                  "camera_connected": False, "note": "No camera status check in this bridge"})

    def do_POST(self):
        if self.path != "/occupancy":
            return self.respond(404, {"error": "not found"})
        supplied = self.headers.get("X-OM-EDGE-TOKEN", "")
        if not TOKEN or not hmac.compare_digest(supplied, TOKEN):
            return self.respond(401, {"error": "unauthorized"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 4096:
                return self.respond(413, {"error": "event size invalid"})
            event = json.loads(self.rfile.read(length))
            store = str(event.get("store_id", ""))[:50]
            camera = str(event.get("counter_id", ""))[:50]
            if not store or not camera or not all(c.isalnum() or c in "-_" for c in store + camera):
                return self.respond(400, {"error": "invalid store/counter identifier"})
            customers = int(event["customer_count"])
            staff = int(event["staff_count"])
            now = dt.datetime.now(dt.timezone.utc).timestamp()
            result = MONITOR.evaluate(store + ":" + camera, customers, staff, now)
            if result["should_alert"]:
                result["speaker"] = speak_homeassistant("Front counter assistance needed. Please return to the counter.")
                print(json.dumps({"time": dt.datetime.now(dt.timezone.utc).isoformat(),
                                  "store": store, "counter": camera,
                                  "alert": "unattended_counter", "speaker": result["speaker"]}), flush=True)
            self.respond(200, result)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self.respond(400, {"error": "invalid occupancy event"})


if __name__ == "__main__":
    if not TOKEN or len(TOKEN) < 24:
        raise SystemExit("Set a secret OM_EDGE_TOKEN of at least 24 characters before starting the local server")
    host = os.getenv("OM_EDGE_BIND", "127.0.0.1")
    port = int(os.getenv("OM_EDGE_PORT", "8765"))
    print(f"OM AI edge event bridge listening on {host}:{port}; no camera connected by default")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
