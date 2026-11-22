#!/usr/bin/env python3
"""Send aggregate camera counts/health, NEVER video, to the private OM AI GAS endpoint.
Run from local cron/scheduler about every 5 minutes after both endpoints are configured.
"""
import os, json, base64, hmac, hashlib, datetime as dt
from pathlib import Path
from urllib.request import Request,urlopen
from analytics import AnalyticsStore

ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'cameras.json').read_text())

def sign_payload(payload: dict, secret: str) -> dict:
    raw=json.dumps(payload,separators=(',', ':'),ensure_ascii=False).encode('utf-8')
    return {'payload':base64.b64encode(raw).decode('ascii'),
            'signature':hmac.new(secret.encode('utf-8'),raw,hashlib.sha256).hexdigest()}

def push():
    url=os.getenv('OM_CAMERA_SYNC_URL','')
    secret=os.getenv('OM_CAMERA_SYNC_SECRET','')
    if not url.startswith('https://') or '/exec' not in url or len(secret)<32:
        raise SystemExit('Configure HTTPS OM_CAMERA_SYNC_URL ending /exec and OM_CAMERA_SYNC_SECRET (32+ chars)')
    store=AnalyticsStore(os.environ.get('OM_SURVEILLANCE_DB',str(ROOT/'surveillance.sqlite3')),CONFIG)
    rows=store.hourly(days=2)
    # Use small bounded batches to avoid Apps Script request/runtime limits.
    chunks=[rows[i:i+100] for i in range(0,len(rows),100)] or [[]]
    for idx, chunk in enumerate(chunks):
        payload={'store_id':CONFIG['store_id'], 'sent_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                 'hours':chunk, 'cameras':store.health() if idx==0 else []}
        data=json.dumps(sign_payload(payload,secret)).encode('utf-8')
        req=Request(url,data=data,method='POST',headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=25) as res:
            result=json.loads(res.read().decode('utf-8'))
            if not result.get('ok'):
                raise RuntimeError('Signed CameraSync ingestion was rejected: '+str(result.get('error','unknown'))[:200])
            print('batch',idx+1,'of',len(chunks),json.dumps(result))

if __name__=='__main__':push()
