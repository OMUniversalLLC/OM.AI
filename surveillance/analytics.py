"""OM AI edge event normalizer and privacy-limited counting store.

Runs locally. Ingests tracked-object END events from Frigate/NVR analytics.
No face, plate, voice, identity inference, or footage leaves the site.
"""
from __future__ import annotations

import datetime as dt
import json
import sqlite3
import threading
from pathlib import Path
from zoneinfo import ZoneInfo

def load_camera_config():
    root = Path(__file__).resolve().parent
    local = root / "cameras.local.json"
    path = local if local.is_file() else root / "cameras.json"
    return json.loads(path.read_text(encoding="utf-8-sig"))


ALLOWED_METRICS = {
    'vehicle_entry', 'vehicle_exit', 'road_vehicle', 'pump_dwell',
    'store_door_entry', 'carwash_entry', 'carwash_exit', 'delivery_vehicle',
    'fuel_transaction', 'carwash_paid', 'carwash_controller_cycle',
    'counter_wait_alert'
}
CONFIRMED_TYPES = {'fuel_transaction', 'carwash_paid', 'carwash_controller_cycle'}
OBJECT_LABELS = {'person', 'car', 'truck', 'motorcycle'}


def utc_hour(iso: str) -> str:
    when = dt.datetime.fromisoformat(iso.replace('Z', '+00:00'))
    if when.tzinfo is None:
        raise ValueError('Timestamp needs a timezone offset')
    return when.astimezone(dt.timezone.utc).replace(minute=0, second=0, microsecond=0).isoformat().replace('+00:00', 'Z')


def time_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def classify_frigate(payload: dict, configs: dict) -> dict | None:
    """Translate a *completed* Frigate tracked object into one zone-level observation.

    This is not a line-crossing detector: a road observation means a tracked
    vehicle was observed in a configured zone, with possible occlusion/error.
    """
    if payload.get('type') != 'end':
        return None
    obj = payload.get('after') or {}
    cam_id = str(obj.get('camera', ''))
    cfg = configs.get(cam_id)
    if not cfg or not cfg.get('enabled', False) or cfg['role'] in {'activity_only','counter_occupancy'}:
        return None
    label = str(obj.get('label', ''))
    if label not in OBJECT_LABELS or label not in cfg['objects']:
        return None
    entered = obj.get('entered_zones') or []
    if cfg['zone'] not in entered:
        return None
    start = obj.get('start_time')
    end = obj.get('end_time')
    if end is None or start is None:
        return None
    dwell = max(0, float(end) - float(start))
    if dwell < cfg.get('minimum_dwell_seconds', 0):
        return None
    tracking_id = str(obj.get('id', '')).strip()
    if not tracking_id or len(tracking_id) > 120:
        return None
    confidence = obj.get('score', None)
    if confidence is not None and (float(confidence) < 0.45 or float(confidence) > 1):
        return None
    iso = dt.datetime.fromtimestamp(float(end), tz=dt.timezone.utc).isoformat().replace('+00:00', 'Z')
    return {
        'event_key': f'frigate:{cam_id}:{tracking_id}:{cfg["role"]}',
        'camera_id': cam_id, 'metric': cfg['role'], 'occurred_at': iso,
        'source': 'camera_detection', 'confidence': confidence,
    }


class AnalyticsStore:
    """SQLite backed, idempotent aggregation with per-camera heartbeat status."""
    def __init__(self, path: str, config: dict):
        self.path = path
        self.config = config
        self.camera_by_id = {c['id']: c for c in config['cameras']}
        if len(self.camera_by_id) != len(config['cameras']):
            raise ValueError('Duplicate camera identifiers')
        self.timezone = ZoneInfo(config['timezone'])
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.executescript('''
           CREATE TABLE IF NOT EXISTS observations (
             event_key TEXT PRIMARY KEY, camera_id TEXT NOT NULL, metric TEXT NOT NULL,
             occurred_at TEXT NOT NULL, hour_bucket TEXT NOT NULL, source TEXT NOT NULL,
             confidence REAL);
           CREATE INDEX IF NOT EXISTS observations_hour_idx ON observations(hour_bucket);
           CREATE TABLE IF NOT EXISTS camera_health (
             camera_id TEXT PRIMARY KEY, last_heartbeat TEXT NOT NULL, status TEXT NOT NULL);
        ''')
        self.conn.commit()

    def add(self, event: dict) -> dict:
        metric = str(event.get('metric',''))
        if metric not in ALLOWED_METRICS:
            raise ValueError('Unsupported observation metric')
        camera = str(event.get('camera_id',''))
        if camera not in self.camera_by_id and camera != 'POS':
            raise ValueError('Camera ID is not in the approved configuration')
        if metric in ('fuel_transaction','carwash_paid') and event.get('source') != 'pos_import':
            raise ValueError('Paid/fuel transactions require a POS import')
        if metric == 'carwash_controller_cycle' and event.get('source') != 'wash_controller':
            raise ValueError('Completed washes require controller evidence')
        if metric == 'counter_wait_alert' and event.get('source') != 'counter_monitor':
            raise ValueError('Counter alerts require a monitored occupancy rule')
        if metric not in CONFIRMED_TYPES and camera == 'POS':
            raise ValueError('POS is only for confirmed records')
        if metric not in CONFIRMED_TYPES and camera != 'POS':
            cfg = self.camera_by_id[camera]
            if not cfg.get('enabled', False):
                raise ValueError('Camera analytics not validated/enabled')
            if event.get('source') == 'camera_detection' and metric != cfg.get('role'):
                raise ValueError('Camera event type does not match enabled role')
            if metric == 'counter_wait_alert' and cfg.get('role') != 'counter_occupancy':
                raise ValueError('Counter monitoring not configured for this camera')
        source = str(event.get('source',''))
        if source not in ('camera_detection','pos_import','wash_controller','counter_monitor'):
            raise ValueError('Invalid source')
        event_key = str(event.get('event_key', ''))
        if not (5 <= len(event_key) <= 180) or any(ord(c) < 32 for c in event_key):
            raise ValueError('Event key missing or invalid')
        stamp = str(event.get('occurred_at',''))
        hour = utc_hour(stamp)
        event_dt = dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))
        if abs((dt.datetime.now(dt.timezone.utc)-event_dt.astimezone(dt.timezone.utc)).total_seconds()) > 7*86400:
            raise ValueError('Observation outside 7-day ingest window')
        confidence = event.get('confidence')
        if confidence is not None:
            confidence = float(confidence)
            if not 0 <= confidence <= 1:
                raise ValueError('Confidence must be 0–1')
        with self.lock:
            cur = self.conn.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?,?)',
                (event_key,camera,metric,event_dt.astimezone(dt.timezone.utc).isoformat(),hour,source,confidence))
            self.conn.commit()
            return {'ok': True, 'created': bool(cur.rowcount), 'metric': metric, 'camera_id': camera}

    def heartbeat(self, camera_id: str, status: str = 'online') -> dict:
        if camera_id not in self.camera_by_id:
            raise ValueError('Unknown camera')
        if status not in ('online','offline'):
            raise ValueError('Invalid heartbeat status')
        now = time_now()
        with self.lock:
            self.conn.execute('INSERT OR REPLACE INTO camera_health VALUES (?,?,?)',(camera_id,now,status))
            self.conn.commit()
        return {'camera_id': camera_id,'status':status,'last_seen':now}

    def health(self):
        with self.lock:
            data = {x[0]: {'last_seen':x[1],'status':x[2]} for x in self.conn.execute('SELECT * FROM camera_health')}
        now = dt.datetime.now(dt.timezone.utc)
        result=[]
        for camera in self.config['cameras']:
            seen=data.get(camera['id'])
            if seen is None:
                status='not_connected'
            else:
                age=(now-dt.datetime.fromisoformat(seen['last_seen'].replace('Z','+00:00'))).total_seconds()
                status='offline' if seen['status']=='offline' else ('online' if age <= 150 else 'stale')
            result.append({'camera_id':camera['id'], 'status':status,
                           'last_seen':seen['last_seen'] if seen else None})
        return result

    def hourly(self, days: int = 2) -> list[dict]:
        start=(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
        with self.lock:
            rows=self.conn.execute('''SELECT camera_id,metric,hour_bucket,source,COUNT(*)
             FROM observations WHERE occurred_at >= ?
             GROUP BY camera_id,metric,hour_bucket,source ORDER BY hour_bucket''',(start,)).fetchall()
        return [{'camera_id':r[0],'metric':r[1],'hour_bucket':r[2],'source':r[3],'count':r[4]} for r in rows]

    def summary(self, day: str) -> dict:
        try: selected_day=dt.date.fromisoformat(day)
        except ValueError as e: raise ValueError('Invalid YYYY-MM-DD') from e
        with self.lock:
            rows=self.conn.execute('SELECT metric,occurred_at FROM observations').fetchall()
        total={}
        for metric,stamp in rows:
            day_in_store=dt.datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(self.timezone).date()
            if day_in_store==selected_day:
                total[metric]=total.get(metric,0)+1
        health=self.health()
        return {'store_id': self.config['store_id'], 'date':day,
                'metrics':total, 'cameras_online':sum(h['status']=='online' for h in health),
                'camera_health':health,'footnotes': [
                  'Pump dwell does NOT prove gas was dispensed.',
                  'Store door entries are people, NOT vehicle-to-store conversion.',
                  'Road-zone detections are observations, NOT independently calibrated official traffic counts.',
                  'Completed car washes require the controller; paid washes require POS confirmation.'
                ]}
