#!/usr/bin/env python3
"""Generate a DISABLED-by-default Frigate camera skeleton from the 14-camera plan.
Camera-zone polygons in this generated file are placeholders and MUST be edited
against each actual camera view before enabling; no connection or counting happens.
"""
from pathlib import Path
import json

root=Path(__file__).resolve().parent
config=json.loads((root/'cameras.json').read_text())
lines=["# OM AI — 14 proposed channels; all DISABLED until RTSP URLs and zones verified.",
       "# Do not publish RTSP credentials or this completed config to public GitHub.",
       "mqtt:","  host: MQTT_BROKER_PRIVATE_HOST","  user: MQTT_USER_REPLACE","  password: MQTT_PASSWORD_REPLACE",
       "cameras:"]
for c in config['cameras']:
    name=c['id']; items=", ".join(c['objects'])
    lines.extend([f"  {name}:","    enabled: false",f"    # {c['name']} — {c['task']}",
      "    ffmpeg:","      inputs:","        - path: rtsp://REPLACE_USER:REPLACE_PASS@REPLACE_CAMERA_IP/REPLACE_PATH",
      "          roles: [detect]", "    objects:", f"      track: [{items}]", "    detect:", "      enabled: true"])
    if c['role'] not in ('activity_only','counter_occupancy'):
        lines.extend(["    zones:",f"      {c['zone']}:",
          "        # REPLACE THESE example polygon coordinates after reviewing this camera!",
          "        coordinates: 0.1,0.1,0.9,0.1,0.9,0.9,0.1,0.9",
          f"        objects: [{items}]"])
    lines.append('')
(root/'frigate.DISABLED.example.yml').write_text('\n'.join(lines)+'\n')
print('Generated Frigate skeleton for',len(config['cameras']),'camera channels. ALL DISABLED.')
