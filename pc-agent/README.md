# OM PC Intelligence + OM AI Orchestrator

**Purpose:** Read-only Windows PC telemetry and proof-of-execution health checks for the private OM AI dashboard.

## Install on the store's Windows 11 PC (authorized administrator)

1. Install Python 3.11 or newer, from an approved source. Use a dedicated non-admin user if possible.
2. From the `pc-agent` directory: `py -m pip install -r requirements.txt`.
3. Copy `config.example.json` to `config.local.json` and adjust **only known** protected process names, drive, thresholds, and jobs. Never add camera or router passwords.
4. Run `py agent.py --config config.local.json --dry-run` to verify. If a temperature sensor is not available, it displays **not measured**, not an invented temperature.
5. Run `py agent.py --config config.local.json` to write local telemetry under private `pc-agent/data/`.
6. Create a Windows Task Scheduler task with **Start in** the `pc-agent` directory, **Program** `py`, **Arguments** `agent.py --config config.local.json`, scheduled every 5 minutes. Test manually first.

Never run as an unattended administrator unless approved security requirements demand it. No remote control and no system optimization take place.

## Temperature and GPU telemetry

Windows `psutil` does NOT generally provide reliable Ryzen CPU/GPU temperature or integrated AMD GPU utilization. Use a separately tested, local sensor integration if the PC exposes real sensors. LibreHardwareMonitor is one option; make it accessible only to the local machine, and validate exact CPU/GPU labels. Do not expose its web server to the internet. Some releases have reported WMI interface problems; plan for data unavailable.

A trusted local sensor collector can write a file `data/sensors.json`, for example:

```json
{"measured_at":"2026-11-19T15:00:00Z","source":"LibreHardwareMonitor","cpu_temp_c":62.4,"gpu_temp_c":55.0,"gpu_util_pct":23.0}
```

Only values with timestamps less than 10 minutes old are accepted. The agent **does not** start LHM automatically or invent temperature readings.

## Job intelligence receipts

The agent cannot independently infer that GasBuddy, AAA, MostEdge, Gemini, or OpenAI jobs succeeded. They must be attached to a real scheduler or audited human workflow. A job runner writes `data/job-receipts.json` with `job_id`, `status`, `finished_at`, `evidence_ref`, and `detail`. See `data.example-job-receipts.json`.

**For execution quality:** `healthy` requires a current successful receipt, plus an HTTPS evidence link when `evidence_required` is true. A missing, failed, stale, incomplete or unreviewed job gets an explicit status. Marking a task verified in the UI records a review; it **does not execute** the job or alter its status.

## Optional private Google Apps Script sync

- In private Apps Script Script Properties, set `OM_PC_SYNC_SECRET` to a random secret of **at least 32 characters**.
- On the store PC, set matching environment variable `OM_PC_SYNC_SECRET`, and `OM_PC_SYNC_URL` to your authorized `https://script.google.com/macros/s/.../exec` URL. Never paste keys in GitHub, Google Sheets cells or ChatGPT.
- Agent signs each JSON payload using HMAC-SHA256 and timestamps; server verifies before storing status-only data in private Sheets.
- If the sync fails, it saves local status and reports a generic error (no secrets or usernames). The remote dashboard marks stale reports as stale.
- An Apps Script deployment that accepts externally submitted signed POSTs requires careful configuration and a private data-access policy; **never expose response data publicly**.

## Safety limitations

- No remote shell, no process kill, no priority or fan setting changes, no cache cleanup, no system reboot, no forced updates.
- It does **not** connect to NVR or stop camera recording. Dedicated camera/network health modules remain authoritative for recording/stream status.
- User identities, raw command lines, process arguments, file paths, raw video, and credentials are not transmitted.
- Aggregate process names and resource values can still be operationally sensitive. Restrict dashboard access to authorized managers.
- Rules are operational heuristics; they are not medical/device-safety guarantees or a substitute for OEM diagnostics.

## Tests

`py -m unittest discover -s tests -v`
