# OM AI counter assistance — local event bridge

This is a **working alert-state service**, not a live computer vision model. It **does not** connect to any camera or automatically detect people. Connect an approved on-prem camera analytics/NVR system that sends counts for each *designated customer zone* and *staff zone*.

## Configuration

1. Keep this behind the store LAN or authenticated reverse proxy. Set `OM_EDGE_TOKEN` to a long random token, and give it only to the trusted local analytics sender. Default listening interface is `127.0.0.1`.
2. Optionally provide `HA_URL`, `HA_TOKEN`, `HA_TTS_ENTITY`, `HA_MEDIA_PLAYER` for a compatible Home Assistant speaker. Without these, alerts log but do not speak.
3. Run `python3 counter_alert.py`. This is Python standard-library only.
4. From your trusted on-prem NVR analytics bridge, POST a JSON event to `http://127.0.0.1:8765/occupancy` with the `X-OM-EDGE-TOKEN` header:

```json
{"store_id":"QUICKC","counter_id":"main","customer_count":1,"staff_count":0}
```

5. The alert fires only if the customer zone remains occupied without staff for 25 seconds and at least 2 observations; it cools down for 120 seconds. Send occupancy events regularly to establish persistence. If events stop arriving, the system cannot know the counter's state and must be treated as **unknown**.

**Privacy / safety:** Do not use biometric recognition, name customers, infer sensitive traits, or broadcast identifying details. Announce neutral staff-assistance prompts only. Obtain appropriate approval for camera/speaker use and secure the camera network. Human review of false-positive alerts is recommended. Never put raw CCTV footage or access tokens in GitHub Pages or public Google Sheets.

## Tests

`python3 -m unittest -v test_counter_alert.py` from this directory.
