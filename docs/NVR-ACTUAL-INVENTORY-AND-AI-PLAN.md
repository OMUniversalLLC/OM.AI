# OM AI — ACTUAL NVR HARDWARE PROFILE (19 November 2026)

Source: user-supplied “Store AI Surveillance — Equipment, Progress and Complete Plan”. This is an equipment report, not a new remote test or live connection.

## Corrections to earlier OM AI prototype

- Previous CAM01–CAM14 assignments (driveway, road, car wash, etc.) were **hypothetical**, not the owner's camera inventory.
- The `surveillance/cameras.json`, Apps Script camera seed and preview in this edition now use the **actual recorder inventory** below.
- **All 14 AI analytics are disabled by default** and show `not_connected`. RTSP playback was demonstrated for channels 1 and 2 only; other channel/name mappings are unverified.
- No road-facing camera, car-wash entrance/exit or wash-bay camera is identified by the supplied list. Camera angles require physical verification before assigning these roles.

## Confirmed equipment and limitations

- NVR marketed as iLink Professionals **iSNVR32P-4K3**; native AI switched on, line-crossing options visible. No saved person event proven yet.
- Existing NVR retains original recording; approximately 7.45 TB cyclic storage was reported. Verify fresh playback, disk health and overwrite before stressing it.
- Tested ONVIF discovery of 14 stream options and RTSP camera 1 and 2 from store PC. Do not expose NVR ports or place credentials in the repo.
- Computer: GMKtec NucBox M7 Ultra; Windows 11 Pro; AMD Ryzen 7 PRO 6850U; 16 GB RAM (12.8 GB Windows usable), integrated AMD Radeon; all-camera inference capacity unknown.
- Last NVR entrance experiment: FRONT DOOR OUTSIDE, native NVR line crossing, People selected, A→B, 24/7, sensitivity 50; **save and successful trigger not verified**. Draw line across actual walking path, verify direction and event footage.

## Actual NVR camera list — do not assume list position equals validated RTSP channel

| # | Actual name | Possible future metric (ONLY after viewing + calibration) |
|---|---|---|
| 1 | SIDE VIEW | vehicle entry candidate |
| 2 | KITCHEN | kitchen operations |
| 3 | FRONT DOOR OUTSIDE | store door entry candidate |
| 4 | THIRD AISLE | aisle activity |
| 5 | REGISTER OUTSIDE | counter view candidate |
| 6 | PUMP SIDE VIEW | pump dwell candidate |
| 7 | SECOND AISLE | aisle activity |
| 8 | REGISTER TOP | counter occupancy candidate |
| 9 | INSIDE COOLER | cooler operations |
| 10 | FIRST AND SECOND AILE | aisle activity |
| 11 | REGISTER | counter occupancy candidate |
| 12 | CHIPS AISLE | aisle activity |
| 13 | BEER COOLER | cooler operations |
| 14 | FRONT DOOR INSIDE | door count crosscheck |

## Start with these proof-of-function tests

1. Verify post-AI NVR recording for all cameras and current playback; test disk retention. Confirm clock/timezone before AI reporting.
2. Complete/save one native NVR person line-crossing rule for **FRONT DOOR OUTSIDE** and observe ten controlled arrivals/departures in each intended direction. Record event time, snapshot and misses.
3. Confirm the same person's crossing is not counted twice when using **FRONT DOOR INSIDE** for validation.
4. Check what **PUMP SIDE VIEW** actually captures. Compare a short manual vehicle tally with detector output. **Pump presence is not fuel purchase.**
5. Choose whether **REGISTER** or **REGISTER TOP** shows both sides of the counter. Calibrate customer vs staff zones. Do NOT activate speaker until unattended waiting detection has been verified.
6. Inspect **SIDE VIEW** and other exterior camera perspectives for a safe driveway or road counting line. Otherwise install/reposition a suitable camera.
7. Confirm whether there are *other* cameras that show car wash entry/exit. If not, car-wash cycles should be sourced from its controller and paid sales from POS instead.
8. Benchmark optional PC inference on one low-resolution RTSP substream first at ~3–5 *analyzed* FPS, then step up only if CPU/RAM/decoder stable. Keep NVR continuous recording unaffected.

## AI model selection

- **Phase 1: Native NVR AI, no extra vision model.** Its person/motor vehicle line-crossing engine is already enabled and should be functionally tested.
- **Phase 2: Small ONNX object detection + tracker**, only if needed for pump dwell, people counting and counter zones. On Windows use CPU baseline, then benchmark Windows ML / ONNX Runtime with compatible GPU execution provider. A detector gives person/vehicle bounding boxes; a tracker + calibrated zones + directional counting rules give events. An LLM cannot replace frame-based counting.
- **Optional later: Frigate**, provided the chosen Linux/ROCm/hardware path is benchmarked. It is not assumed to be plug-and-play for this AMD integrated GPU.
- Check training weights and software licenses for business deployment, including commercial/AGPL conditions for specific model vendors.
- AI may summarize stored *events* into staff reports; do not continuously upload raw video to a cloud LLM or make automatic claims of criminal behavior.

## Store-system boundaries

- `vehicle_entry`/`road_vehicle` = camera observations only after proper line calibration; never official road AADT.
- `pump_dwell` = vehicle observed in pump zone for chosen duration, never proven fuel dispense.
- `fuel_transaction` = authorized POS transaction import, not vehicle identity.
- `store_door_entry` = directional person crossing; cannot directly establish exact fuel-to-store conversion without reliable linkage.
- `carwash_controller_cycle` = controller-confirmed cycle; `carwash_paid` = POS-confirmed paid wash.
- `counter_wait_alert` = validated staff-assistance event, not a personnel misconduct determination.

## Integration in this source pack

- `surveillance/cameras.json`: actual inventory + proposed tasks; analytics disabled, no credentials.
- `apps-script/CameraSync.gs`: seeds *correct actual names* for new private OM AI Sheets.
- For an existing Sheet seeded with old example names, explicitly run `omAlignCameraNamesToActualNvr('REPLACE_HYPOTHETICAL_CAMERA_PLAN')` **after reviewing custom changes**; it resets names, roles, status and tasks for the 14 known IDs but does not touch NVR or enable live feeds.
- `surveillance/analytics.py` now rejects camera counts from camera roles that are not explicitly validated/enabled, or that mismatch the configured role.
- `/counter` is disabled until the actual REGISTER camera has been tested for explicit customer + staff zones.
- The HTML preview has actual names but `not_connected` statuses and zero camera readings.

## Security

Keep local RTSP URLs/private NVR addresses and passwords only on the store computer or a secrets manager. Do not place recordings, keys, passwords or network topology in a public GitHub Pages site. Use secure access and role restrictions for remote video. The NVR must keep recording locally even when the internet is down.

## Status

This pack updates the **code and setup plan only**. It has not connected to, tested, reconfigured or deployed the physical NVR or any camera, store PC, POS, wash controller or Google Sheet.
