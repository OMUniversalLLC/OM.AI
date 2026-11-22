# OM AI WiFi Intelligence — Store Windows PC

This monitor runs on a Windows PC alongside a locally configured recorder. It never makes network-wide scans and does not alter router/NVR settings. All data stays local unless you explicitly enable signed export.

## What it actually knows

- **Known equipment**: the owner-configured NVR/router/PC IPs and TCP ports are checked. A successful TCP handshake proves *that TCP service responded*, not that recording or Wi-Fi is healthy. Two failures become `suspected_offline`, not a certain power outage.
- **Camera feeds**: 14 verified camera names are in the JSON config; all 14 checks are **disabled** initially. For each channel you explicitly verify and enable, optional FFprobe checks whether a stream can be read. Playback is not proof that the NVR is recording; use the NVR's Record indicator and sample playback.
- **Local network neighbors**: Windows `arp -a` provides a *cache* of recently observed neighbors, not the router's connected-client list. Unknown neighbors are labeled "unrecognized — review" and never automatically "unauthorized".
- **Actual associated Wi-Fi clients**: requires an authorized router client export/API. A CSV is supported as an input; its age and association state are surfaced. Router association is distinct from a device responding to TCP.
- **Wi-Fi link rate**: optional receive/transmit connection speed of the PC's Wi-Fi interface, **not** an internet speed test or bandwidth use by other devices.
- **Wi-Fi signal**: `netsh wlan show interfaces` measures only Wi-Fi on the **monitoring PC**. If the PC is wired, it does not measure your store's access point signal or customers' Wi-Fi.

## Windows installation — start safely with local-only testing

1. Keep this directory in a secure folder on your **store PC**, not a publicly readable shared drive. Python 3.10+ is required. No pip install is needed for basic monitoring.
2. Copy `config.example.json` to `config.json`. The NVR's prior private LAN address is already listed as the one approved test target. Confirm that it is still correct before running. The router and store PC entries are intentionally blank.
3. Open PowerShell in this directory and run:

   ```powershell
   py -3 monitor.py --once
   ```

   Local report: `private/latest.json`. It won't log Wi-Fi passwords or save video.
4. Check the **NVR web client** to verify that all 14 cameras are online and recording, and independently test recent playback. Compare with the local report.
5. To monitor regularly (without uploading anything):

   ```powershell
   py -3 monitor.py --loop
   ```

   This uses the configured interval (minimum 60 seconds; sample is 300 seconds). When you confirm it behaves correctly, configure Windows Task Scheduler to start it under a dedicated restricted Windows account at logon/startup. Do not run it as system administrator just to read network status.

## Actual Wi-Fi client lists

The best source for "which devices are connected to Wi-Fi" is your **router/access point controller's associated-clients list**, if its model supports a permitted export or read-only API. Do not assume `arp -a` proves association.

Optional router CSV schema:

```csv
hostname,ip,mac,connection,status
Example-Kiosk,192.168.50.120,00-11-22-33-44-55,wifi,connected
```

Place it in a secure local folder, configure the `router_clients_csv` path (e.g. `C:\\OM-AI\\router-clients.csv`), and ensure the export is regularly refreshed. Files older than `router_export_max_age_minutes` are explicitly marked unverified. Do not upload raw MAC exports to the public site.

## Optional camera stream checks

The existing report only verified RTSP playback for channel 1, and channel 2 substream playback, **not** the actual mapping of all 14 camera labels. For one channel at a time:

1. Independently verify the NVR channel/physical camera label and current recording.
2. Install official FFmpeg with `ffprobe` available on PATH.
3. Set a local environment variable, e.g. `OM_WIFI_RTSP_CAM01`, to the RTSP substream URL. Use a restricted video-reader account and never put URLs containing credentials in GitHub, Apps Script, browser storage, or Google Sheets.
4. Set `channel_mapping_verified` and `probe_enabled` to `true` for that one camera in `config.json`.
5. Test the result before enabling any other channel. Keep camera checks modest: FFprobe starts a short stream read at the configured polling interval.

**Security caveat:** On Windows, process arguments can be visible to local administrators/process tools while FFprobe runs. Use a dedicated least-privilege camera account, secure the PC, and revoke it if exposed. The system never uploads the RTSP URL or credentials.

## Optional private OM AI website sync

Use a **separate signed ingest deployment** of the OM AI Apps Script project, configured to execute as the owner and allow POST access. The signed intake rejects requests with invalid signatures; the main dashboard must remain Google-login protected. Review exposure/rate limits before enabling the public POST endpoint. Never publish private records through the existing GitHub Pages site.

1. Add `WifiMonitor.gs` and the updated existing files to your **private OM AI** Apps Script project.
2. In its Script Properties, set a strong random `OM_WIFI_SYNC_SECRET` (at least 32 characters, different from the camera sync secret).
3. Run `setupOmAi()` as the owner to create the new `NetworkStatus`, `NetworkDevices`, `NetworkCameras`, and `NetworkEvents` private Sheet tabs. This addition does not overwrite existing camera or sales tabs.
4. Deploy the restricted dashboard and independently test the signed ingestion web deployment. Configure `OM_WIFI_SYNC_URL` and `OM_WIFI_SYNC_SECRET` **only on the store PC**, not in public repository files.
5. From PowerShell after verifying local results:

   ```powershell
   $env:OM_WIFI_SYNC_URL = 'https://script.google.com/macros/s/YOUR_DEPLOYMENT/exec'
   $env:OM_WIFI_SYNC_SECRET = 'REPLACE_WITH_A_LONG_RANDOM_PRIVATE_SECRET'
   $env:OM_WIFI_HASH_SALT = 'ANOTHER_LONG_RANDOM_LOCAL_SALT'
   py -3 monitor.py --sync
   ```

   In production, store environment variables/secrets in an access-controlled local service account context (not in a shared startup script or transcript).
6. The new **OM WiFi** tab shows the reported measurements. The dashboard marks data **stale after 15 minutes** and shows offline *suspicions*, not fake all-clear.

A web app executing as the accessing Google user may require login for its POST route and therefore **cannot necessarily accept unauthenticated Python uploads**. Separate dashboard/ingest deployment modes must be tested; if your Apps Script configuration doesn't support this safely, use a dedicated authenticated backend instead. Do not weaken dashboard access just to make sync work.

## Network safety and retention

- All checks are for the store network you manage. Only the configured private IPs receive an active TCP connection attempt.
- Never open router, NVR, ONVIF, RTSP or Windows remote-control ports to the public internet. The store PC makes outbound HTTPS requests if sync is enabled.
- **No Wi-Fi password recovery**, brute force, device blocking, audio capture, facial identification or covert tracking is included.
- `private/latest.json` is not intended for cloud sync. The `.gitignore` excludes the private folder and credentials.
- The central Sheet contains IPs and masked MACs as sensitive operational data: grant only authorized employees access, use MFA, and determine appropriate retention.
- Unknown neighbors need human verification, especially visitor/customer devices on a separate guest network.
- Real camera/NVR failures should be confirmed through the NVR's channel health and actual recording/playback—not just a TCP/RTSP failure.

## Tests

```powershell
py -3 -m unittest discover -s tests -v
```

See `docs/WIFI-INTELLIGENCE.md` in the main project for the integrated data flow and UI description.
