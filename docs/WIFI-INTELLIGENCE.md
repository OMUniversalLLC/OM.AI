# OM WiFi Intelligence — Surveillance and Store Network Monitoring

**Status:** Source code + local demo complete, **not deployed or connected to store devices**.

## New dashboard section

OM WiFi provides five views on one desktop/mobile page: PC Wi-Fi condition, known device reachability, recent ARP/router observations, each of 14 NVR channel stream checks, and timestamped status changes. Nothing should be shown as live until a signed store-agent heartbeat is received.

### Equipment configuration

Keep actual equipment and channel names in the private site profile. The public configuration uses sample labels. The Wi-Fi dashboard displays a connection type when the router, controller, or recorder provides evidence.

## Data flow

```text
Store router/client roster ──(optional approved CSV/export)──┐
Windows Wi-Fi interface state (store PC) ─────────────────────┤
Known router/NVR/PC IP/port checks ───────────────────────────┤
Passive Windows ARP neighbor cache ──────────────────────────┤
Optional per-channel RTSP/FFprobe checks ────────────────────┤
                                                            ▼
                                           OM WiFi agent on store PC
                                            │ local private JSON
                                            └─ optional signed HTTPS POST
                                                       ▼
                                             Apps Script intake
                                                       ▼
                                          Private Google Sheets
                                                       ▼
                                          Authenticated OM AI website
```

## Database changes

| Sheet | Purpose |
|---|---|
| `NetworkStatus` | One snapshot of PC connection and last reported freshness per store |
| `NetworkDevices` | Last observed state per configured target or cache/router neighbor |
| `NetworkCameras` | Optional RTSP stream response by actual NVR camera ID |
| `NetworkEvents` | Change-only status log with a stable event key |

Network health is **not** a camera surveillance detector, customer counter or security verdict. Its alerts are limited to NVR/network reachability suspicion and stream-check failures.

## Differences between online, offline and unknown

- `reachable`: configured TCP port replied on that private IP.
- `no_response`: one local TCP check failed; not proof of failure.
- `suspected_offline`: repeated configured checks failed; investigate locally.
- `observed_in_cache`: IP/MAC was seen in a recent Windows neighbor cache; connection not verified.
- `router_reported_connected`: a recent authorized router export reported association; does not prove app responsiveness.
- `stale`: no new agent snapshot within 15 minutes; unknown **regardless** of previous status.
- `stream_playable`: FFprobe accessed a selected RTSP feed, when user configured it.
- `probe_failed`: the RTSP check failed; may be credentials, codec, network or stream mapping—not definitive camera outage.

## Suggested observer responsibilities

- **Opening shift**: check NVR recording status, overnight outages, WAN/ISP/router status and expected Wi-Fi clients.
- **Every shift**: review offline-suspected devices, verify camera snapshots/recording when a stream probe fails, check store POS connectivity and terminal availability.
- **Closing shift**: confirm each of 14 camera recordings from a recent timestamp; check critical network alarms were acknowledged.
- **Weekly**: review router DHCP / access-point association records, tag unknown devices after investigation, audit users and check backups.

Never automatically label a nearby/customer device as malicious, and never block a device solely because it appears unrecognized.

## Later router integration

To show true live connected Wi-Fi client names, signal strength per client, access point association and bandwidth, we need the router/access-point **brand/model** and its documented API or authorized export. The Windows neighbor cache cannot provide that information. If separate access points are used, their controller may be the source instead of the ISP gateway.

## Sources

- Windows network neighbor cache: https://learn.microsoft.com/en-us/powershell/module/nettcpip/get-netneighbor
- Windows Wi-Fi interface status: https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-wlan
- Windows network adapter metadata: https://learn.microsoft.com/en-us/powershell/module/netadapter/get-netadapter

The attached NVR inventory is user-reported; no remote device was accessed by the development environment. Test every integration onsite before relying on alerts.
