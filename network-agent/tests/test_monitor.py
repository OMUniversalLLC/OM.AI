import importlib.util
import json
from pathlib import Path
from unittest import TestCase, mock
import unittest

P=Path(__file__).resolve().parents[1]/'monitor.py'
spec=importlib.util.spec_from_file_location('om_wifi_monitor',P)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class TestOmWifiMonitor(TestCase):
    def test_arp_is_passive_and_limited_to_approved_lan(self):
        arp='''Interface: 192.168.50.11 --- 0x10\n  192.168.50.10  aa-bb-cc-dd-ee-01 dynamic\n  192.168.50.45  aa-bb-cc-dd-ee-03 dynamic\n  8.8.8.8 aa-bb-cc-dd-ee-06 dynamic\n  192.168.50.255 ff-ff-ff-ff-ff-ff static'''
        found=m.parse_arp(arp,['192.168.50.0/24'])
        self.assertEqual(len(found),2)
        self.assertEqual(found[0]['ip'],'192.168.50.10')
    def test_wifi_measurement_is_monitoring_pc_only(self):
        s='  State : connected\n  SSID : Quick-C\n  Signal : 72%\n  Receive rate (Mbps) : 144.4\n  Transmit rate (Mbps) : 144.4'
        self.assertEqual(m.pc_wifi_status(s)['signal_pct'],72)
        self.assertEqual(m.pc_wifi_status('')['state'],'not_available')
    def test_two_failures_become_suspected_not_verified_camera_outage(self):
        cfg={'devices':[{'id':'NVR','name':'NVR','type':'nvr','host':'192.168.50.10','tcp_port':81,'critical':True}]}
        with mock.patch.object(m,'tcp_probe',return_value={'ok':False,'reason':'tcp_unreachable','latency_ms':None}):
            first=m.monitored_devices(cfg)[0];self.assertEqual(first['status'],'no_response')
            second=m.monitored_devices(cfg,{'NVR':first})[0];self.assertEqual(second['status'],'suspected_offline')
    def test_no_configuration_does_not_claim_camera_online(self):
        c={'id':'CAM03','name':'Camera 03','channel_mapping_verified':False,'probe_enabled':False}
        self.assertEqual(m.verify_camera_stream(c)['status'],'not_configured')
    def test_public_address_not_probed(self):
        self.assertEqual(m.tcp_probe('8.8.8.8',53)['reason'],'non_private_address_refused')
    def test_snapshot_has_no_secrets_and_unrecognized_not_unauthorized(self):
        cfg={'store_id':'QUICKC','allowed_subnets':['192.168.50.0/24'],
             'devices':[{'id':'NVR','name':'iLink','type':'nvr','host':'192.168.50.10','tcp_port':81}],
             'cameras':[{'id':'CAM01','name':'SIDE VIEW','probe_enabled':False,'channel_mapping_verified':False}]}
        arp='192.168.50.55  00-11-22-33-44-55 dynamic'
        with mock.patch.object(m,'tcp_probe',return_value={'ok':True,'latency_ms':10,'reason':'tcp_open'}):
            report=m.collect_snapshot(cfg,windows={'wifi':'','arp':arp})
        self.assertTrue(any(d['status']=='observed_in_cache' for d in report['devices']))
        self.assertTrue(all('unauthorized' not in d['status'] for d in report['devices']))
        self.assertEqual(report['cameras'][0]['status'],'not_configured')
        self.assertNotIn('password',json.dumps(report).lower())
    def test_signing_verifiable(self):
        secret='long-secret-32-plus-chars-please-123456789'
        p={'kind':'wifi_snapshot','store_id':'QUICKC','sent_at':'2026-11-19T00:00:00Z'}
        data=m.signed_envelope(p,secret)
        import base64,hmac,hashlib
        raw=base64.b64decode(data['payload'])
        self.assertTrue(hmac.compare_digest(data['signature'],hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()))

if __name__=='__main__': unittest.main()
