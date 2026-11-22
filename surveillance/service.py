#!/usr/bin/env python3
"""Private LAN listener for authorized local analytics events (no video upload)."""
import json
import os
import hmac
import datetime as dt
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from analytics import AnalyticsStore, classify_frigate, load_camera_config
from sys import path as sys_path
sys_path.insert(0, str(Path(__file__).resolve().parents[1] / 'edge-agent'))
from counter_alert import CounterMonitor, speak_homeassistant

ROOT = Path(__file__).resolve().parent
CONFIG = load_camera_config()
STORE = AnalyticsStore(os.environ.get('OM_SURVEILLANCE_DB', str(ROOT / 'surveillance.sqlite3')), CONFIG)
COUNTER = CounterMonitor(wait_seconds=float(os.environ.get('OM_WAIT_SECONDS','25')),
                         cooldown_seconds=float(os.environ.get('OM_ALERT_COOLDOWN','120')))
TOKEN = os.getenv('OM_EDGE_TOKEN','')

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body=json.dumps(data).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def authorized(self):
        return TOKEN and hmac.compare_digest(TOKEN, self.headers.get('X-OM-EDGE-TOKEN',''))

    def do_GET(self):
        if not self.authorized(): return self.reply(401,{'error':'Unauthorized'})
        p=urlparse(self.path)
        if p.path=='/health':
            return self.reply(200,{'service':'OM AI surveillance event collector','status':'running',
              'note':'Only camera heartbeats establish camera connection status', 'cameras': STORE.health()})
        if p.path=='/summary':
            day=parse_qs(p.query).get('date',[dt.datetime.now(STORE.timezone).date().isoformat()])[0]
            try: return self.reply(200,STORE.summary(day))
            except ValueError as e:return self.reply(400,{'error':str(e)})
        if p.path=='/hours':return self.reply(200,{'counts':STORE.hourly()})
        return self.reply(404,{'error':'Not found'})

    def do_POST(self):
        if not self.authorized():return self.reply(401,{'error':'Unauthorized'})
        length=int(self.headers.get('Content-Length','0'))
        if length<=0 or length>12000:return self.reply(413,{'error':'Invalid size'})
        try:
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('JSON object required')
            p=urlparse(self.path).path
            if p=='/frigate':
                event=classify_frigate(data,STORE.camera_by_id)
                return self.reply(200, STORE.add(event) if event else {'ok':True,'counted':False})
            if p=='/observation':return self.reply(200,STORE.add(data))
            if p=='/heartbeat':return self.reply(200,STORE.heartbeat(str(data.get('camera_id','')),str(data.get('status','online'))))
            if p=='/counter':
                camera='CAM11'  # actual NVR 'REGISTER' camera; must be calibrated first
                camera_config=STORE.camera_by_id[camera]
                if not camera_config.get('enabled',False) or camera_config.get('role')!='counter_occupancy':
                    return self.reply(409,{'error':'Counter analytics are not configured or validated for CAM11'})
                customer=int(data['customer_count']);staff=int(data['staff_count'])
                result=COUNTER.evaluate(CONFIG['store_id']+':'+camera,customer,staff,dt.datetime.now(dt.timezone.utc).timestamp())
                if result['should_alert']:
                    obs={'event_key':'counter:'+dt.datetime.now(dt.timezone.utc).isoformat(), 'camera_id':camera,
                         'metric':'counter_wait_alert','occurred_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                         'source':'counter_monitor','confidence':None}
                    STORE.add(obs)
                    result['speaker']=speak_homeassistant('Assistance requested at the front counter.')
                return self.reply(200,result)
            return self.reply(404,{'error':'Not found'})
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as e:
            return self.reply(400,{'error':str(e)[:200]})

if __name__=='__main__':
    if len(TOKEN)<24:raise SystemExit('Set OM_EDGE_TOKEN (24+ random characters)')
    bind=os.getenv('OM_EDGE_BIND','127.0.0.1');port=int(os.getenv('OM_SURVEILLANCE_PORT','8766'))
    print(f'OM AI surveillance listener on {bind}:{port}; no video is uploaded')
    ThreadingHTTPServer((bind,port),Handler).serve_forever()
