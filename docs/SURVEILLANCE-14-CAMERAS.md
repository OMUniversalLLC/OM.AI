> **SUPERSEDED CAMERA NAMES**: The CAM01–CAM14 labels below were an initial hypothetical layout. Use the actual camera list and safety gates in `NVR-ACTUAL-INVENTORY-AND-AI-PLAN.md` and `surveillance/cameras.json`. The old suggested dedicated road/car-wash cameras are **not verified** by the real NVR inventory.

# OM AI — 14-camera surveillance, traffic, fuel funnel and car wash monitor

**Implementation stage:** Usable local event collector, optional Frigate/MQTT adapter, Apps Script aggregate ingestion, dashboard UI and simulated browser preview. **No cameras or store POS hardware are connected to this package.** Every camera-to-zone assignment below is a proposed template, NOT a claim about the store's actual 14 camera angles.

## Core metrics (avoid false claims)

| What user wants | Data feed | Metric | What it actually means |
|---|---|---|---|
| How many cars enter the station? | CAM01 driveway entry track + calibrated ROI | `vehicle_entry` | Number of distinct vehicle tracks seen in the entrance zone, subject to occlusion/false detection |
| How many cars leave? | CAM02 | `vehicle_exit` | Observed departures; not always equal arrivals (lag, missed objects, parked cars) |
| Road traffic outside the store | CAM03 road-facing view with privacy masking | `road_vehicle` | Unique tracked vehicle observations in a zone; not official FDOT AADT, directional traffic, or speed |
| How many cars stop at a pump? | CAM04–06 pump zones + >=30 sec dwell | `pump_dwell` | Vehicles observed near pump for a minimum dwell, NOT verified dispensing |
| How many actually buy gas? | Authorized fuel POS/EOD report with stable receipt IDs | `fuel_transaction` | Recorded fuel transactions, NOT unique cars or confirmed gallon amounts |
| How many people enter the store? | CAM08 inside-store entrance line/zone | `store_door_entry` | Person detections at store door; distinguish in vs out via calibrated line crossing to call it *entries* |
| Which fuel buyers DID NOT enter the store? | Requires privacy-respecting cross-channel session linkage and POS, or opt-in loyalty/receipt linking | **UNKNOWN until reliable linkage is installed** | Dividing store-door people by gas transactions is NOT buyer conversion |
| How many cars enter car wash? | CAM11 | `carwash_entry` | Arrivals to wash entrance, not actual washes |
| How many cars leave car wash? | CAM12 | `carwash_exit` | Exits; can include aborts/detours |
| How many cycles complete? | Car-wash controller integration | `carwash_controller_cycle` | Verified completed physical wash cycles; **not** automatically paid |
| How many paid washes? | Car-wash sales/POS | `carwash_paid` | Paid washes recorded by POS; reconcile to cycles |
| Road accidents / construction | FDOT / FL511 or TomTom APIs separately | External OM Radar source | Outside camera by itself cannot validate an accident cause or projected construction date |
| Customer waiting; counter unattended | CAM09 *separately configured* customer and staff occupancy analytics | `counter_wait_alert` | Local event rule (>=25 sec, >=2 samples, cooldown) announces generic staff-assistance message |

### 14-camera proposed role mapping

`surveillance/cameras.json` contains CAM01–CAM14, assigned in the following order: entrance, exit, road frontage, north pumps, south pumps, diesel pumps, forecourt, store entrance, checkout, sales floor, wash entrance, wash exit, wash bay, deliveries/rear. **Change these to reflect the actual DVR channels before enabling detection.** If one camera covers more than one zone, counts may require a separate tracked-object/ROI adapter to avoid duplicating a person or vehicle.

## Components

```text
RTSP-capable NVR/IP camera streams (owned/licensed on-site; existing DVR)
            |
Frigate NVR (optional local machine)  -- Frigate's own authenticated live view
       | MQTT 'frigate/events' after tracked object ends
       v
surveillance/mqtt_bridge.py (optional paho-mqtt)
       | POST /frigate + local token
       v
surveillance/service.py (127.0.0.1:8766 by default)
       | verify camera ID, entered zone, class, minimum dwell, track ID, timestamp
       v
SQLite deduplicated observations, local health and hourly counts
       | scheduled surveillance/sync_to_apps_script.py (hourly buckets only, NO video)
       | HTTPS signed HMAC-SHA256 payload -> deployed private Apps Script /exec
       v
CameraSync.gs (verifies signature, freshness, allowed types and store)
       | new CameraConfig, CameraHour, CameraChecks tabs
       v
OM Cameras dashboard (authorized Google account, browser/mobile)

Frigate local stats -> surveillance/frigate_health.py -> /heartbeat
Counter customer/staff occupancy -> /counter -> existing Home Assistant TTS bridge
POS fuel receipts -> /observation (source=pos_import) -> fuel transaction counts
Car-wash controller -> /observation (source=wash_controller) -> finished cycles
```

## Setup part A — Google Apps Script

1. In the **separate private OM AI Apps Script project**, add `CameraSync.gs` alongside existing OM AI code; update `Config.gs`, `Api.gs`, `Setup.gs`, `Client.html`, `Styles.html`. **Do not overwrite** the unrelated original management dashboard's `doGet()`.
2. In Apps Script **Project Settings → Script Properties** set `OM_CAMERA_SYNC_SECRET` to a randomly generated 32+ character secret; do not place it in Google Sheets or GitHub. Copy the same secret to the local machine environment.
3. Run `setupOmAi()` as owner again. It creates 3 new tabs and seeds **14 proposed camera records** without changing existing sales records. **Back up the private Sheet before running migrations.**
4. Run `createOmCameraDailyChecks()` and optionally `installOmAiCameraDailyChecks()` as owner. The trigger uses the Apps Script project timezone; set it to America/New_York for Plant City. Assign observers via OM Cameras screen; a daily checklist is created on the approximate chosen hour.
5. Deploy/update the OM AI **web app** (`Deploy → Manage deployments`). For signed machine-to-machine POSTs, the `/exec` URL must accept the request without interactive Google login. This means deploying an endpoint accessible to external clients (often `Anyone`), relying on the HMAC signature and strict validation. **Keep all database/dashboard read and write operations gated by existing Google identity checks.** If your organization disallows public POST endpoints, use a private gateway instead of this Apps Script endpoint.
6. Test account restrictions with an Admin, Manager and Viewer. The authorized dashboard remains private even when the machine ingestion route is reachable. Never share the private source Sheet with viewers who should not read it directly.

## Setup part B — local edge computer and NVR

1. Use a dedicated on-site PC/mini-PC/server connected to the DVR/cameras by a restricted LAN/VLAN. RTSP/ONVIF support depends on your exact DVR/camera manufacturer. Obtain proper admin-authorized stream URLs and hardware credentials **locally**, never paste passwords into chat or source code.
2. Install [Frigate](https://docs.frigate.video/guides/getting_started/) on that machine if using its tracking. Copy `surveillance/frigate.DISABLED.example.yml`, replace MQTT details and RTSP URLs *locally*, and draw actual polygons for each camera using Frigate's zones editor. **All generated camera entries start `enabled: false`; do not turn on until the camera, zone and object classes are tested.** Name Frigate camera entries `CAM01`, etc., or edit `cameras.json` accordingly.
3. Test object detection accuracy at varying light, shadows, glare, occlusions and rain. For **road traffic direction/speed**, implement a calibrated line-crossing tracker (or use FDOT/traffic vendor data). This MVP counts distinct tracks seen in the road zone; it does not infer direction or speed.
4. Set a strong local token, start the edge listener, and (optionally) install paho MQTT:

```bash
cd surveillance
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-optional.txt
export OM_EDGE_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(42))')"
export OM_SURVEILLANCE_DB="$(pwd)/surveillance.sqlite3"
python3 service.py
```

In another shell with the same `OM_EDGE_TOKEN`:

```bash
export OM_MQTT_HOST='YOUR_LOCAL_BROKER'
export OM_MQTT_USER='YOUR_BROKER_USER'
export OM_MQTT_PASSWORD='YOUR_BROKER_PASSWORD'
python3 mqtt_bridge.py
```

To poll a privately hosted Frigate instance's stream health once per minute (via system scheduler):

```bash
export OM_FRIGATE_URL='https://YOUR_PRIVATE_FRIGATE_HOST'
python3 frigate_health.py
```

5. Set `OM_CAMERA_SYNC_URL` to the deployed OM AI Apps Script `/exec` and set **the same** `OM_CAMERA_SYNC_SECRET` as in Apps Script script properties; run `python3 sync_to_apps_script.py` manually, inspect `{ "ok": true, ... }`, and then install an OS cron/systemd scheduled task every 5–15 minutes. This sends **only hourly counts and heartbeat status**, no camera media, faces, identities, or license plates.
6. In dashboard, use **OM Cameras** on desktop/mobile to view updated aggregates and observer tasks. Dashboard refresh is manual. For footage, open your **secured local NVR** separately over LAN/VPN. Do not expose RTSP feeds directly on GitHub Pages or in Google Sheets.

### Optional local event examples

These are for **testing only**, not replacements for real detector/POS/controller events.

```bash
curl -X POST http://127.0.0.1:8766/heartbeat -H "X-OM-EDGE-TOKEN: $OM_EDGE_TOKEN" -H 'Content-Type: application/json' -d '{"camera_id":"CAM01","status":"online"}'

curl -X POST http://127.0.0.1:8766/observation -H "X-OM-EDGE-TOKEN: $OM_EDGE_TOKEN" -H 'Content-Type: application/json' -d '{"camera_id":"POS","event_key":"fuel-receipt-0001","metric":"fuel_transaction","source":"pos_import","occurred_at":"2026-11-19T14:04:00Z"}'

curl -X POST http://127.0.0.1:8766/counter -H "X-OM-EDGE-TOKEN: $OM_EDGE_TOKEN" -H 'Content-Type: application/json' -d '{"customer_count":1,"staff_count":0}'
```

Note: the receipt example uses a fixed date and will be rejected if sent more than seven days away from execution. Use the current UTC time in an actual test. Real POS receipt IDs must be stable and unique to avoid duplicate counting.

## Speaker notifications

`surveillance/service.py` reuses the existing `edge-agent/counter_alert.py` code. To use audio prompts, configure a valid Home Assistant service URL, bearer token, TTS entity, and media player (`HA_URL`, `HA_TOKEN`, `HA_TTS_ENTITY`, `HA_MEDIA_PLAYER`) on the local computer. It only announces **“Assistance requested at the front counter.”** once a separate occupancy detector sends repeated unattended-counter signals lasting at least 25 seconds; it cools down for 120 seconds. It cannot infer customer vs. employee roles from a bare Frigate `person` label; configure explicit zones/analytics input. No automatic microphone recording.

## Accuracy and privacy safeguards

- Reconcile camera pump visits with real fuel **transactions** without falsely treating them as the same number of vehicles. Compare car wash entries/exits with controller cycles and paid washes, tracking gaps for review. Any exact vehicle-to-store conversion rate requires validated cross-channel linkage; leave it **unavailable** otherwise.
- Physical camera perspective and object detection quality determine whether all arrivals are seen. Retain camera event ID only for deduplication, not personal identity.
- Keep raw video/stream credentials on site; aggregate counts only in Sheets. Use VPN and role-based authorization for live video; rotate secrets and maintain audit logs. Do not film bathrooms or other private spaces; position road camera to avoid unnecessary capture of neighboring private property.
- Florida restricts interception/recording of protected oral communications under Fla. Stat. §934.03; **do not enable ambient audio recording** without legal review/appropriate consent. Outgoing staff speaker announcements do not require listening to customer conversations. Inform employees about workplace video monitoring and check applicable signage/retention requirements.
- Separate **camera offline** alerts (explicit heartbeat health) from **zero vehicles observed**; missed updates are unknown, not zero.
- Treat camera estimates as measurements with uncertainty; conduct manual observations and POS reconciliation before relying on business forecasts.
- Frigate detector/storage sizing depends on the actual 14 feed resolutions, codec, FPS, recording retention, hardware acceleration and AI detector. Benchmark before promising real-time performance.

## Status summary

**Implemented:** 14-role config, disabled Frigate template generator, secure local API, MQTT adapter, heartbeat poller, counter speaker integration, deduplicated SQLite, hourly export and signed Apps Script intake, new Sheets tabs and daily observer check workflow, OM Cameras responsive UI and fictional preview, unit/browser tests.

**Not connected:** Your actual 14 cameras, DVR, microphone/speaker, live RTSP/video preview, fuel POS, car wash controller or production Google Sheet. No confirmed purchase counts can be shown until authorized source events arrive. This code does not connect to MostEdge or cloud surveillance vendors by itself.
