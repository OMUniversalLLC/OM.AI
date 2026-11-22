#!/usr/bin/env python3
"""OM PC Intelligence + OM Orchestrator, Windows-oriented, read-only by design.

Collects bounded, sanitized machine telemetry and evaluates operator-provided job
receipts. It NEVER kills processes, changes settings, invokes LLMs, or opens ports.
Local files stay under private data/ and are excluded from source control.
"""
from __future__ import annotations
import argparse
from collections import deque
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

try:
    import psutil
except ImportError:
    psutil = None

HERE = Path(__file__).resolve().parent
UTC = timezone.utc


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_time(value: str) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return t.astimezone(UTC) if t.tzinfo else None
    except (ValueError, TypeError):
        return None


def clamp_num(value, low=0., high=100.) -> float | None:
    try:
        n = float(value)
        if not (low <= n <= high):
            return None
        return round(n, 1)
    except (ValueError, TypeError, OverflowError):
        return None


def text(value, maximum=120) -> str:
    return ''.join(c for c in str(value or '') if c.isprintable())[:maximum]


def read_json(path: Path, fallback):
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json_atomic(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    tmp.replace(path)


def hardware_sensors() -> dict:
    """Temperature / GPU use external sensor receipt, NOT a fabricated Windows reading.

    Optional trusted local collector writes `data/sensors.json`:
      {"measured_at":"...Z","cpu_temp_c":56,"gpu_temp_c":52,
       "gpu_util_pct":23,"source":"LibreHardwareMonitor"}
    This agent will not start sensors with admin privileges or expose an LHM server.
    """
    data = read_json(HERE / 'data' / 'sensors.json', {})
    measured_at = parse_time(data.get('measured_at', ''))
    fresh = bool(measured_at and utcnow() - measured_at < timedelta(minutes=10) and measured_at <= utcnow() + timedelta(minutes=1))
    out = {'source': text(data.get('source')) if fresh else 'not_configured',
           'measured_at': iso(measured_at) if fresh else None,
           'cpu_temp_c': None, 'gpu_temp_c': None, 'gpu_util_pct': None}
    if fresh:
        out['cpu_temp_c'] = clamp_num(data.get('cpu_temp_c'), 0, 125)
        out['gpu_temp_c'] = clamp_num(data.get('gpu_temp_c'), 0, 125)
        out['gpu_util_pct'] = clamp_num(data.get('gpu_util_pct'), 0, 100)
    return out


def machine_metrics(config: dict, ps=psutil) -> dict:
    """No process command lines, owner names, paths, browsing info or raw MACs."""
    sensor = hardware_sensors()
    result = {'status': 'unavailable', 'cpu_pct': None, 'ram_pct': None, 'ram_used_gb': None,
              'ram_available_gb': None, 'disk_pct': None, 'disk_free_gb': None,
              'gpu_pct': sensor['gpu_util_pct'], 'cpu_temp_c': sensor['cpu_temp_c'],
              'gpu_temp_c': sensor['gpu_temp_c'], 'sensor_source': sensor['source'],
              'uptime_hours': None, 'processes': [], 'critical_services': [],
              'cpu_cores_logical': None, 'note': ''}
    if ps is None:
        result['note'] = 'Install psutil on the Windows store PC to collect CPU/RAM/disk/process telemetry.'
        return result
    try:
        memory = ps.virtual_memory()
        disk = ps.disk_usage(config.get('disk_path') or os.path.abspath(os.sep))
        result.update({'status': 'measured', 'cpu_pct': clamp_num(ps.cpu_percent(interval=0.3)),
           'ram_pct': clamp_num(memory.percent), 'ram_used_gb': round(memory.used/2**30,2),
           'ram_available_gb': round(memory.available/2**30,2),
           'disk_pct': clamp_num(disk.percent), 'disk_free_gb': round(disk.free/2**30,1),
           'uptime_hours': round((utcnow().timestamp()-ps.boot_time())/3600,1),
           'cpu_cores_logical': ps.cpu_count(logical=True)})
        tracked={text(p).lower() for p in config.get('protected_processes', [])}
        services=[]
        aggregates={}
        # CPU% from single quick psutil snapshot is approximate; do not claim it is precise
        for p in ps.process_iter(['name','memory_info','cpu_percent']):
            try:
                name=text(p.info.get('name'),65).lower()
                if not name or not re.fullmatch(r'[a-z0-9_.() -]{1,65}',name):
                    continue
                v=aggregates.setdefault(name, {'name':name,'count':0,'ram_mb':0.,'cpu_pct':0.,'protected':name in tracked})
                v['count']+=1
                mem=p.info.get('memory_info')
                v['ram_mb']+= (getattr(mem,'rss',0) or 0) / 2**20
                v['cpu_pct']+=float(p.info.get('cpu_percent') or 0)
            except (ps.NoSuchProcess, ps.AccessDenied, AttributeError, ValueError):
                continue
        data=sorted(aggregates.values(), key=lambda x:x['ram_mb'], reverse=True)
        for row in data[:12]:
            row['ram_mb']=round(row['ram_mb'],1)
            row['cpu_pct']=round(row['cpu_pct'],1)
        # Core services status is advisory based on presence, not OS service manager state.
        services=[{'name':name, 'status':'process_seen' if name in aggregates else 'not_seen',
                   'note':'Process name match only; not proof of recorder/service health'} for name in sorted(tracked)[:15]]
        result['processes']=data[:12]
        result['critical_services']=services
        return result
    except (OSError, ValueError) as exc:
        result['note']='Windows metrics read error: '+type(exc).__name__
        return result


def assess_pc(m: dict, thresholds: dict, previous: list | None=None) -> list:
    """Conservative diagnostics; no automatic action or unsafe process kill."""
    prev = previous or []
    def persistent(key, boundary):
        recent=[x.get('pc',{}) for x in prev[-2:] if isinstance(x,dict)]
        return len(recent)==2 and all(isinstance(x.get(key),(int,float)) and x[key]>=boundary for x in recent)
    r=[]
    def alert(code, severity, title, detail, suggestion):
        r.append({'code':code,'severity':severity,'title':title,'detail':detail,'recommendation':suggestion,'approval_required':True})
    if m.get('status') != 'measured':
        alert('agent_setup','medium','PC telemetry unavailable','CPU/RAM/process measurements are unavailable.','Install psutil and verify Windows monitoring permissions.')
        return r
    ram_limit=thresholds.get('ram_warning_pct',85)
    cpu_limit=thresholds.get('cpu_warning_pct',85)
    if m['ram_pct'] is not None and m['ram_pct']>=ram_limit:
        alert('ram_pressure','high' if persistent('ram_pct',ram_limit) else 'medium', 'RAM pressure detected',
              f"RAM use {m['ram_pct']}%. Investigate sustained use and memory growth.",
              'Review high-memory noncritical apps and browser tabs; close only with operator approval. Keep surveillance/recording processes protected.')
    if m['cpu_pct'] is not None and m['cpu_pct']>=cpu_limit:
        alert('cpu_pressure','high' if persistent('cpu_pct',cpu_limit) else 'medium','CPU load elevated',
              f"CPU load {m['cpu_pct']}%; verify whether the camera decoder or AI inference is overloaded.",
              'Reduce OPTIONAL AI inference frame rate or number of analyzed streams after a measured test. Do not reduce NVR recording quality by default.')
    if m.get('cpu_temp_c') is None:
        alert('temp_unavailable','info','CPU temperature not measured','Windows CPU heat cannot be inferred from CPU load alone.',
              'Configure a local, read-only hardware sensor export and validate sensor labels; do not assume the PC is cool.')
    elif m['cpu_temp_c']>=thresholds.get('cpu_temp_warning_c',85):
        alert('cpu_hot','high','CPU temperature needs attention',f"CPU sensor reported {m['cpu_temp_c']}°C.",
              'Check ventilation and dust, inspect fan operation, and reduce optional AI load with permission. Inspect OEM thermal guidance.')
    if m.get('disk_free_gb') is not None and m['disk_free_gb'] < thresholds.get('disk_free_warning_gb',20):
        alert('disk_low','high','Low disk free space',f"PC disk has {m['disk_free_gb']} GB free.",
              'Review log retention and backups; never delete NVR footage or business records automatically.')
    for s in m.get('critical_services',[]):
        if s['status']=='not_seen':
            alert('critical_not_seen_'+s['name'],'medium','Configured critical process not observed',
                  f"No running process name matched {s['name']}. This does not prove the NVR is offline.",
                  'Check Windows service name and approved process inventory, then verify actual camera recording separately.')
    return r[:25]


VALID_JOB_STATES={'success','failed','running','skipped','needs_review'}

def evaluate_jobs(definitions: list, receipts: list, now: datetime) -> list:
    """No evidence -> never mark complete; absent receipt -> not connected / overdue.
    A receipt is written only by an approved job runner after the attempt, not inferred
    from task name or a scheduled trigger existing.
    """
    by_id={}
    for x in receipts:
        jid=x.get('job_id')
        t=parse_time(x.get('finished_at',''))
        if jid and t and (jid not in by_id or t>by_id[jid][0]):
            by_id[jid]=(t,x)
    out=[]
    for d in definitions[:80]:
        jid=text(d.get('job_id'),50)
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_\-]{2,49}', jid): continue
        hours=max(1,min(24*31,int(d.get('max_age_hours',24))))
        owner=text(d.get('owner'),60)
        r=by_id.get(jid)
        latest=r[1] if r else {}
        finish=r[0] if r else None
        age=round((now-finish).total_seconds()/3600,1) if finish else None
        state='not_connected'
        if finish and age>=0:
            if latest.get('status')=='failed': state='failed'
            elif age>hours: state='overdue'
            elif latest.get('status')=='running': state='running'
            elif latest.get('status')=='skipped': state='skipped'
            elif latest.get('status')=='needs_review': state='needs_review'
            elif latest.get('status')=='success':
                # Successful HTTP request alone is not sufficient evidence when source verification is required
                state='healthy' if (not d.get('evidence_required') or str(latest.get('evidence_ref','')).startswith('https://')) else 'needs_evidence'
            else: state='needs_review'
        out.append({'job_id':jid,'name':text(d.get('name'),90),'provider':text(d.get('provider'),45),
                   'owner':owner, 'state':state,'last_run':iso(finish) if finish else None,
                   'max_age_hours':hours,'age_hours':age,'evidence_ref':text(latest.get('evidence_ref'),300) if state=='healthy' else '',
                   'detail':text(latest.get('detail'),180), 'next_action':{
                    'not_connected':'Connect an authorized source or publish a signed job receipt.',
                    'overdue':'Check the scheduler, credentials and source availability.',
                    'failed':'Inspect error logs and retry using the approved provider integration.',
                    'needs_evidence':'Attach verifiable evidence and have a reviewer confirm data quality.',
                    'needs_review':'Review output for completeness before marking complete.',
                    'skipped':'Confirm why this run was skipped.',
                    'running':'Wait for job result; inspect hung worker if run exceeds its timeout.',
                    'healthy':'No action required; next run remains scheduled.'}[state]})
    return out


def correlate(pc: dict, jobs: list, alerts: list) -> list:
    """Cross-signal hypotheses are suggestions; not proof of cause."""
    findings=[]
    byid={j['job_id']:j for j in jobs}
    if pc.get('ram_pct') is not None and pc['ram_pct']>=85 and any('camera' in j['name'].lower() and j['state'] in ('failed','overdue') for j in jobs):
        findings.append({'title':'Camera analytics delay alongside RAM pressure',
                         'assessment':'Possible shared-resource contention; correlation is not proof of cause.',
                         'next_step':'Review process memory trend and camera worker logs before reducing optional inference.'})
    failing=[j for j in jobs if j['state'] in ('failed','overdue')]
    if len(failing)>=3:
        findings.append({'title':'Several scheduled tasks unhealthy',
                         'assessment':'Possible shared dependency issue or multiple independent failures.',
                         'next_step':'Verify internet and Apps Script health, then isolate each provider; do not blindly retry all jobs.'})
    return findings[:10]


def build_snapshot(config: dict, receipts: list, previous: list | None=None, now:datetime|None=None) -> dict:
    now=now or utcnow()
    pc=machine_metrics(config)
    jobs=evaluate_jobs(config.get('jobs',[]),receipts,now)
    alerts=assess_pc(pc,config.get('thresholds',{}),previous)
    insights=correlate(pc,jobs,alerts)
    return {'kind':'pc_task_snapshot','store_id':str(config.get('store_id','QUICKC')),
            'device_id':text(config.get('device_id','STORE-PC-01'),40),
            'sent_at':iso(now), 'pc':pc,'jobs':jobs,'alerts':alerts,'insights':insights,
            'safety':'Read-only diagnostics; no process changes or remote execution.'}


def sign_snapshot(snapshot:dict,secret:str) -> dict:
    if len(secret)<32: raise ValueError('OM_PC_SYNC_SECRET must contain >=32 characters')
    raw=json.dumps(snapshot, separators=(',',':'),ensure_ascii=False).encode('utf-8')
    return {'kind':'pc_task_snapshot','payload':base64.b64encode(raw).decode('ascii'),
            'signature':hmac.new(secret.encode('utf-8'),raw,hashlib.sha256).hexdigest()}


def sync(endpoint:str,envelope:dict) -> dict:
    if not endpoint.startswith('https://script.google.com/'):
        raise ValueError('Only your Google Apps Script HTTPS endpoint is accepted')
    req=urllib.request.Request(endpoint,json.dumps(envelope).encode('utf-8'),{'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req,timeout=25) as r:
        reply=json.loads(r.read(8000).decode('utf-8'))
    if not reply.get('ok'): raise RuntimeError('Ingestion failed; inspect authorized Apps Script logs')
    return reply


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Read-only PC and task intelligence agent')
    p.add_argument('--config',default=str(HERE/'config.example.json'))
    p.add_argument('--job-receipts',default=str(HERE/'data'/'job-receipts.json'))
    p.add_argument('--dry-run',action='store_true',help='Print status; never transmit')
    args=p.parse_args(argv)
    cfg=read_json(Path(args.config),{})
    if not cfg: raise SystemExit('Missing config JSON')
    path=HERE/'data'/'history.json'
    history=read_json(path,[])
    if not isinstance(history,list):history=[]
    receipts=read_json(Path(args.job_receipts),[])
    snap=build_snapshot(cfg,receipts if isinstance(receipts,list) else [], history[-3:])
    if args.dry_run:
        print(json.dumps(snap,indent=2));return 0
    write_json_atomic(HERE/'data'/'latest.json',snap)
    history=(history+[{'sent_at':snap['sent_at'],'pc':{k:v for k,v in snap['pc'].items() if k in ('cpu_pct','ram_pct','cpu_temp_c','disk_free_gb')}}])[-1000:]
    write_json_atomic(path,history)
    url=os.environ.get('OM_PC_SYNC_URL','')
    secret=os.environ.get('OM_PC_SYNC_SECRET','')
    if url and secret:
        try:
            result=sync(url,sign_snapshot(snap,secret));print('Signed OM AI snapshot uploaded: '+str(result.get('ok')))
        except Exception as exc:
            print('Remote sync unavailable ('+type(exc).__name__+'); local snapshot retained',file=sys.stderr)
            return 2
    else:
        print('Saved private local snapshot; remote sync not configured.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
