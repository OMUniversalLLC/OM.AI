"""All tests use simulated in-memory events; no CCTV or network required."""
from __future__ import annotations
import datetime as dt, json, sys, unittest, copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analytics import AnalyticsStore, classify_frigate, utc_hour
from sync_to_apps_script import sign_payload
import hmac, base64, hashlib

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'cameras.json').read_text())

class AnalyticsTests(unittest.TestCase):
    def setUp(self):self.demo=copy.deepcopy(CONFIG);self.store=AnalyticsStore(':memory:',self.demo)
    def now(self):return dt.datetime.now(dt.timezone.utc)
    def event(self,event_key='cam01-a',metric='vehicle_entry',camera_id='CAM01',source='camera_detection'):
        return {'event_key':event_key,'camera_id':camera_id,'metric':metric,
                'occurred_at':self.now().isoformat(),'source':source,'confidence':0.91}

    def test_14_configured_cameras_and_no_assumed_online(self):
        self.assertEqual(len(CONFIG['cameras']),14)
        self.assertEqual(CONFIG['cameras'][2]['name'],'FRONT DOOR OUTSIDE')
        self.assertTrue(all(not c['enabled'] for c in CONFIG['cameras']))
        self.assertEqual(self.store.health()[0]['status'],'not_connected')
        self.store.heartbeat('CAM01')
        self.assertEqual(self.store.health()[0]['status'],'online')

    def test_dedup_and_hourly(self):
        self.store.camera_by_id['CAM03'].update({'enabled':True,'role':'store_door_entry'})
        self.assertTrue(self.store.add(self.event(camera_id='CAM03',metric='store_door_entry'))['created'])
        self.assertFalse(self.store.add(self.event(camera_id='CAM03',metric='store_door_entry'))['created'])
        rows=self.store.hourly()
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['count'],1)
        self.assertEqual(rows[0]['metric'],'store_door_entry')

    def test_pump_dwell_minimum(self):
        self.store.camera_by_id['CAM06'].update({'enabled':True,'role':'pump_dwell'})
        start=self.now().timestamp()
        obj={'type':'end','after':{'camera':'CAM06','label':'car','id':'xyz',
             'start_time':start-8,'end_time':start,'entered_zones':['pump_side_view'],'score':0.8}}
        self.assertIsNone(classify_frigate(obj,self.store.camera_by_id))
        obj['after']['start_time']=start-45
        event=classify_frigate(obj,self.store.camera_by_id)
        self.assertEqual(event['metric'],'pump_dwell')
        self.assertEqual(event['source'],'camera_detection')
        self.assertTrue(self.store.add(event)['created'])

    def test_nonmatching_zone_and_nonend_not_counted(self):
        self.store.camera_by_id['CAM01'].update({'enabled':True,'role':'vehicle_entry'})
        start=self.now().timestamp()
        ev={'type':'end','after':{'camera':'CAM01','label':'car','id':'xyz',
         'start_time':start-5,'end_time':start,'entered_zones':['sidewalk']}}
        self.assertIsNone(classify_frigate(ev,self.store.camera_by_id))
        ev['after']['entered_zones']=['side_view'];ev['type']='update'
        self.assertIsNone(classify_frigate(ev,self.store.camera_by_id))
        ev['type']='end'
        self.assertEqual(classify_frigate(ev,self.store.camera_by_id)['metric'],'vehicle_entry')

    def test_confirmed_sales_not_inferred_from_camera(self):
        with self.assertRaises(ValueError):self.store.add(self.event(metric='fuel_transaction'))
        with self.assertRaises(ValueError):self.store.add(self.event(metric='carwash_controller_cycle',source='pos_import',camera_id='POS'))
        tx=self.event('receipt-1','fuel_transaction','POS','pos_import')
        wash=self.event('wash-cycle-1','carwash_controller_cycle','POS','wash_controller')
        self.assertTrue(self.store.add(tx)['created'])
        self.assertTrue(self.store.add(wash)['created'])

    def test_timezone_and_store_day(self):
        self.store.camera_by_id['CAM03'].update({'enabled':True,'role':'store_door_entry'})
        event=self.event('tz-01',metric='store_door_entry',camera_id='CAM03')
        self.store.add(event)
        local_day=self.now().astimezone(self.store.timezone).date().isoformat()
        report=self.store.summary(local_day)
        self.assertEqual(report['metrics']['store_door_entry'],1)
        self.assertTrue(any('NOT prove gas' in line for line in report['footnotes']))
        self.assertTrue(utc_hour('2026-11-19T08:34:02+05:30').endswith('03:00:00Z'))

    def test_disabled_camera_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not validated'):
            self.store.add(self.event(metric='store_door_entry',camera_id='CAM03'))
        self.assertIsNone(classify_frigate({'type':'end','after':{'camera':'CAM06'}},self.store.camera_by_id))

    def test_camera_metric_mismatch_rejected(self):
        self.store.camera_by_id['CAM03'].update({'enabled':True,'role':'store_door_entry'})
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.store.add(self.event(metric='road_vehicle',camera_id='CAM03'))

    def test_signed_payload(self):
        secret='z'*42
        bundle=sign_payload({'sent_at':self.now().isoformat(),'hours':[]},secret)
        raw=base64.b64decode(bundle['payload'])
        self.assertTrue(hmac.compare_digest(bundle['signature'],hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()))

if __name__=='__main__':unittest.main(verbosity=2)
