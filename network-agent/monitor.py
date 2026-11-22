#!/usr/bin/env python3
"""OM AI WiFi Intelligence: bounded, read-only monitoring of an OWNED store LAN.

Python 3.10+ stdlib. No network-wide port scanning. Each active TCP check is made
ONLY to an explicitly configured IP. Neighbor discovery is passive and is NOT a
complete/authoritative list of associated Wi-Fi clients.
"""
from __future__ import annotations
import argparse
import base64
import csv
import datetime as dt
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
UTC = dt.timezone.utc
NOW = lambda: dt.datetime.now(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def run_cmd(args, timeout=5):
    try:
        p = subprocess.run(args, capture_output=True, text=True, errors='replace',
                           timeout=timeout, check=False)
        return p.stdout if p.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def pc_wifi_status(text):
    """Only describes WiFi of the MONITORING PC, not the store router or clients."""
    if not text.strip():
        return {'state': 'not_available', 'ssid': '', 'signal_pct': None,
                'receive_mbps': None, 'transmit_mbps': None}
    def field(label):
        found = re.search(r'^\s*' + re.escape(label) + r'\s*:\s*(.+)$', text, re.I | re.M)
        return found.group(1).strip() if found else ''
    raw_signal = field('Signal')
    match = re.search(r'(\d{1,3})\s*%', raw_signal)
    def rate(label):
        try: return float(field(label))
        except ValueError: return None
    state = field('State').lower()
    return {'state': 'connected' if state=='connected' else ('disconnected' if 'disconnected' in state else 'unknown'),
            'ssid': field('SSID'), 'signal_pct': min(100, int(match.group(1))) if match else None,
            'receive_mbps': rate('Receive rate (Mbps)'), 'transmit_mbps': rate('Transmit rate (Mbps)')}


def parse_arp(text, allowed_subnets):
    """Read Windows `arp -a` neighbor cache; do NOT equate this to connected devices."""
    networks = [ipaddress.ip_network(s, strict=False) for s in allowed_subnets]
    out={}
    for line in text.splitlines():
        m=re.match(r'^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-f]{2}(?:[:-][0-9a-f]{2}){5})\s+(\w+)',line,re.I)
        if not m: continue
        try: addr=ipaddress.ip_address(m.group(1))
        except ValueError: continue
        if not any(addr in net for net in networks): continue
        mac=m.group(2).replace(':','-').lower()
        if addr.is_multicast or mac=='ff-ff-ff-ff-ff-ff': continue
        out[str(addr)]={'ip':str(addr),'mac':mac,'cache_state':m.group(3).lower()}
    return list(out.values())


def mask_mac(mac):
    pieces=mac.replace(':','-').split('-')
    return 'XX:XX:XX:'+':'.join(p.upper() for p in pieces[-3:]) if len(pieces)==6 else ''


def tcp_probe(host, port, timeout=1.25):
    try:
        ip=ipaddress.ip_address(host)
        if not ip.is_private: return {'ok':False,'reason':'non_private_address_refused','latency_ms':None}
        if not 1<=int(port)<=65535: raise ValueError('invalid port')
        start=time.monotonic()
        with socket.create_connection((str(ip),int(port)),timeout=timeout): pass
        return {'ok':True,'reason':'tcp_open','latency_ms':round((time.monotonic()-start)*1000)}
    except (OSError, ValueError, TimeoutError):
        return {'ok':False,'reason':'tcp_unreachable','latency_ms':None}


def read_router_clients(path, max_age_minutes=15):
    """Optional authorized export. Stale file NEVER represents live connectivity."""
    if not path: return [],'not_configured'
    p=Path(path)
    if not p.is_file(): return [],'missing_export'
    age=max(0,time.time()-p.stat().st_mtime)
    stale=age>max_age_minutes*60
    try:
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))[:150]
    except (OSError, UnicodeError, csv.Error): return [],'unreadable_export'
    clients=[]
    for row in rows:
        ip=(row.get('ip') or '').strip()
        try:
            if not ipaddress.ip_address(ip).is_private: continue
        except ValueError: continue
        mac=(row.get('mac') or '').strip().lower().replace(':','-')
        wifi=(row.get('connection') or row.get('type') or 'unknown').lower()
        associated=(row.get('status') or '').strip().lower() in ('connected','associated','online')
        clients.append({'ip':ip,'mac':mac,'hostname':(row.get('name') or row.get('hostname') or '')[:75],
                        'connection':'wifi' if wifi in ('wifi','wireless','wlan') else ('wired' if wifi in ('wired','ethernet') else 'unknown'),
                        'state':'router_reported_connected' if associated and not stale else 'router_export_unverified'})
    return clients,'stale' if stale else 'recent_export'


def stable_unknown_id(mac, salt):
    return 'OBS-'+hashlib.sha256((salt+'|'+mac).encode()).hexdigest()[:14].upper()


def verify_camera_stream(camera, configured_env=None):
    """Optional ffprobe test. No full CCTV frames are persisted or exported.

    URLs must be in local ENV variables. Credentials can be visible to local OS process
    monitoring during ffprobe; use a least-privilege RTSP reader account.
    """
    if not camera.get('probe_enabled') or not camera.get('channel_mapping_verified'):
        return {'camera_id':camera['id'],'name':camera['name'],'status':'not_configured',
                'method':'none','details':'Mapping or optional stream probe not enabled'}
    envname = camera.get('rtsp_url_env','')
    url = (configured_env or os.environ).get(envname,'') if re.fullmatch(r'OM_WIFI_RTSP_CAM\d{2}',envname) else ''
    if not url.startswith('rtsp://'):
        return {'camera_id':camera['id'],'name':camera['name'],'status':'not_configured',
                'method':'ffprobe','details':'No local RTSP URL configured'}
    if not shutil.which('ffprobe'):
        return {'camera_id':camera['id'],'name':camera['name'],'status':'not_configured',
                'method':'ffprobe','details':'FFmpeg ffprobe not installed'}
    try:
        p=subprocess.run(['ffprobe','-v','error','-rtsp_transport','tcp','-select_streams','v:0',
              '-show_entries','stream=codec_type','-of','json',url],capture_output=True,
              timeout=8,text=True,check=False)
        playable=p.returncode==0 and 'video' in p.stdout
        return {'camera_id':camera['id'],'name':camera['name'],
                'status':'stream_playable' if playable else 'probe_failed','method':'ffprobe',
                'details':'RTSP stream responded' if playable else 'RTSP did not pass stream check; NVR recording unverified'}
    except (subprocess.TimeoutExpired,OSError):
        return {'camera_id':camera['id'],'name':camera['name'],'status':'probe_failed',
                'method':'ffprobe','details':'Stream probe timed out; recording not checked'}


def monitored_devices(config, previous=None):
    previous=previous or {}; results=[]
    for dev in config.get('devices',[])[:60]:
        host=dev.get('host',''); port=dev.get('tcp_port',0)
        if not host or not port:
            status='not_configured'; latency=None; evidence='No approved host/port configured'; failures=0
        else:
            result=tcp_probe(host,port)
            failures=0 if result['ok'] else int(previous.get(dev['id'],{}).get('failed_checks',0))+1
            status='reachable' if result['ok'] else ('suspected_offline' if failures>=2 else 'no_response')
            latency=result['latency_ms'];evidence='TCP port responsive' if result['ok'] else 'TCP check failed; device may block connections or be asleep'
        results.append({'device_id':dev['id'],'label':dev.get('name',dev['id'])[:80],
            'device_type':dev.get('type','other'),'connection':dev.get('connection','unknown'),
            'ip_address':host if host else '', 'mac_masked':mask_mac(dev.get('mac','')),
            'status':status,'method':'tcp_known_target','last_checked':NOW(),
            'latency_ms':latency,'evidence':evidence,'critical':bool(dev.get('critical',False)),
            'failed_checks':failures})
    return results


def collect_snapshot(config, previous=None, windows=None):
    """windows injectable for unit tests; never auto-probes an entire subnet."""
    windows=windows or {}
    checked=NOW()
    wifi=pc_wifi_status(windows.get('wifi',run_cmd(['netsh','wlan','show','interfaces']) if sys.platform=='win32' else ''))
    devices=monitored_devices(config,previous or {})
    by_ip={x['ip_address']:x for x in devices if x['ip_address']}
    allowed=config.get('allowed_subnets',['192.168.50.0/24'])
    cache=parse_arp(windows.get('arp',run_cmd(['arp','-a'])),allowed)
    salt=os.environ.get('OM_WIFI_HASH_SALT','local-temporary-ids')
    for n in cache:
        if n['ip'] in by_ip: continue
        devices.append({'device_id':stable_unknown_id(n['mac'],salt),'label':'Unrecognized network neighbor',
            'device_type':'unknown','connection':'unknown','ip_address':n['ip'],
            'mac_masked':mask_mac(n['mac']),'status':'observed_in_cache','method':'neighbor_cache',
            'last_checked':checked,'latency_ms':None,
            'evidence':'Seen in local ARP cache; not confirmed online or unauthorized','critical':False,'failed_checks':0})
    router_rows,roster_state=read_router_clients(config.get('router_clients_csv',''),config.get('router_export_max_age_minutes',15))
    for n in router_rows:
        if n['ip'] in by_ip:
            by_ip[n['ip']]['connection']=n['connection']
            by_ip[n['ip']]['evidence']+='; router association: '+n['state']
            continue
        found=next((d for d in devices if d['ip_address']==n['ip']),None)
        if found:
            found['connection']=n['connection']
            found['status']=n['state']
            found['method']='router_export'
            found['label']=n['hostname'] or found['label']
            found['evidence']='Router export; check its timestamp and connection status'
        else:
            devices.append({'device_id':stable_unknown_id(n['mac'] or n['ip'],salt),
                'label':n['hostname'] or 'Router-listed device','device_type':'unknown',
                'connection':n['connection'],'ip_address':n['ip'],
                'mac_masked':mask_mac(n['mac']),'status':n['state'],'method':'router_export',
                'last_checked':checked,'latency_ms':None,
                'evidence':'Router report, not independent live network verification','critical':False,'failed_checks':0})
    device_states={d['device_id']:d for d in devices}
    events=[]
    for d in devices:
        before=(previous or {}).get(d['device_id'],{}).get('status')
        if before and before!=d['status'] and d.get('critical'):
            events.append({'device_id':d['device_id'],'kind':'status_changed',
                'severity':'high' if d['status']=='suspected_offline' else 'info',
                'details':d['label']+': '+before+' → '+d['status'], 'occurred_at':checked})
    camera_list=[verify_camera_stream(c) for c in config.get('cameras',[])[:32]]
    return {'kind':'wifi_snapshot','store_id':config['store_id'],'sent_at':checked,
            'pc_wifi':wifi,'router_export_state':roster_state,
            'devices':devices[:100],'cameras':camera_list,'events':events[:30],
            'agent_note':'Read-only known-target probes + passive ARP; cannot prove all associated Wi-Fi devices or NVR recording.'}


def _save_json_atomic(path, obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    temp.replace(path)


def signed_envelope(snapshot,secret):
    if len(secret)<32: raise ValueError('OM_WIFI_SYNC_SECRET must contain at least 32 characters')
    raw=json.dumps(snapshot,separators=(',', ':'),ensure_ascii=False).encode('utf-8')
    return {'kind':'wifi_snapshot','payload':base64.b64encode(raw).decode(),
            'signature':hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()}


def sync_to_apps_script(snapshot):
    endpoint=os.environ.get('OM_WIFI_SYNC_URL','')
    secret=os.environ.get('OM_WIFI_SYNC_SECRET','')
    if not endpoint.startswith('https://') or '/exec' not in endpoint:
        raise ValueError('OM_WIFI_SYNC_URL must be a private HTTPS Apps Script /exec URL')
    envelope=signed_envelope(snapshot,secret)
    data=json.dumps(envelope).encode()
    request=Request(endpoint,data=data,headers={'Content-Type':'application/json'},method='POST')
    with urlopen(request,timeout=25) as response:
        reply=json.loads(response.read().decode('utf-8'))
    if not reply.get('ok'): raise RuntimeError('OM AI rejected the signed network snapshot: '+str(reply.get('error','unknown'))[:150])
    return reply


def main():
    p=argparse.ArgumentParser(description='OM AI read-only WiFi Intelligence agent for YOUR store LAN')
    p.add_argument('--config',default=str(ROOT/'config.json'))
    p.add_argument('--out',default=str(ROOT/'private/latest.json'))
    p.add_argument('--sync',action='store_true',help='Send signed metadata only to private Apps Script')
    p.add_argument('--loop',action='store_true',help='Continue checking at configured intervals')
    args=p.parse_args()
    cfg=json.loads(Path(args.config).read_text(encoding='utf-8'))
    if cfg.get('store_id')!='QUICKC': raise SystemExit('This sample agent currently supports QUICKC; configure other stores separately.')
    prev_path=Path(args.out)
    while True:
        previous={}
        if prev_path.exists():
            try: previous={d['device_id']:d for d in json.loads(prev_path.read_text()).get('devices',[])}
            except (ValueError,OSError,KeyError): pass
        snapshot=collect_snapshot(cfg,previous)
        _save_json_atomic(prev_path,snapshot)
        print(snapshot['sent_at'],'devices=',len(snapshot['devices']),'camera_streams=',len(snapshot['cameras']),
              'camera_probe_success=',sum(c['status']=='stream_playable' for c in snapshot['cameras']))
        if args.sync:
            try: print('Synced:',sync_to_apps_script(snapshot))
            except Exception as err: print('Sync error (local data retained):',str(err)[:180],file=sys.stderr)
        if not args.loop: break
        time.sleep(max(60,min(3600,int(cfg.get('interval_seconds',300)))))

if __name__=='__main__':main()
