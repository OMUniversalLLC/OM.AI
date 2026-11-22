#!/usr/bin/env python3
"""Poll local secured Frigate stats and report real camera stream health.

Designed to run once a minute from a local scheduler; no inbound LAN port is opened.
Frigate camera names must match CAM01..CAM14. No stream or image is transferred.
"""
import json, os
from urllib.request import Request,urlopen
from pathlib import Path

LOCAL=os.getenv('OM_EDGE_URL','http://127.0.0.1:8766').rstrip('/')
FRIGATE=os.environ.get('OM_FRIGATE_URL','').rstrip('/')
TOKEN=os.environ.get('OM_EDGE_TOKEN','')

if __name__=='__main__':
    if not FRIGATE or not TOKEN:
        raise SystemExit('Set OM_FRIGATE_URL (local/NVR) and OM_EDGE_TOKEN')
    if not (FRIGATE.startswith('https://') or FRIGATE.startswith('http://127.0.0.1:') or FRIGATE.startswith('http://localhost:')):
        raise SystemExit('Use secure Frigate HTTPS URL or a localhost proxy, not unencrypted remote HTTP')
    headers={}
    if os.getenv('OM_FRIGATE_API_KEY'):
        headers['Authorization']='Bearer '+os.environ['OM_FRIGATE_API_KEY']
    with urlopen(Request(FRIGATE+'/api/stats',headers=headers),timeout=10) as res:
        data=json.load(res)
    config=json.loads((Path(__file__).resolve().parent/'cameras.json').read_text())
    stats=data.get('cameras') or {}
    for c in config['cameras']:
        name=c['id']
        info=stats.get(name)
        if not info:continue # Unknown, not offline unless explicitly present.
        fps=float(info.get('camera_fps') or 0)
        status='online' if fps>0 else 'offline'
        blob=json.dumps({'camera_id':name,'status':status}).encode('utf-8')
        req=Request(LOCAL+'/heartbeat',data=blob,method='POST',headers={
          'X-OM-EDGE-TOKEN':TOKEN,'Content-Type':'application/json'})
        with urlopen(req,timeout=8) as res:
            res.read()
    print('Frigate health checked for configured camera channels')
