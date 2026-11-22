import unittest
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import agent

class RulesTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,19,15,0,tzinfo=timezone.utc)
        self.jobs=[{'job_id':'aaa_daily','name':'AAA price check','provider':'AAA',
                    'owner':'Fuel team','max_age_hours':27,'evidence_required':True},
                   {'job_id':'camera_analytics','name':'Camera analytics heartbeat',
                    'provider':'Store PC','max_age_hours':1,'evidence_required':False}]
    def test_not_connected_is_not_success(self):
        out=agent.evaluate_jobs(self.jobs,[],self.now)
        self.assertTrue(all(x['state']=='not_connected' for x in out))
    def test_success_must_have_evidence(self):
        out=agent.evaluate_jobs(self.jobs,[{'job_id':'aaa_daily','status':'success','finished_at':'2026-11-19T14:00:00Z'}],self.now)
        self.assertEqual(out[0]['state'],'needs_evidence')
    def test_success_with_url_and_fresh(self):
        out=agent.evaluate_jobs(self.jobs,[{'job_id':'aaa_daily','status':'success','finished_at':'2026-11-19T14:00:00Z','evidence_ref':'https://gasprices.aaa.com/'}],self.now)
        self.assertEqual(out[0]['state'],'healthy')
    def test_failed_and_old(self):
        entries=[{'job_id':'aaa_daily','status':'failed','finished_at':'2026-11-19T14:00:00Z'},
                 {'job_id':'camera_analytics','status':'success','finished_at':'2026-11-19T11:00:00Z'}]
        out=agent.evaluate_jobs(self.jobs,entries,self.now)
        self.assertEqual(out[0]['state'],'failed')
        self.assertEqual(out[1]['state'],'overdue')
    def test_future_receipt_not_accepted(self):
        out=agent.evaluate_jobs(self.jobs,[{'job_id':'aaa_daily','status':'success','finished_at':'2026-11-22T14:00:00Z'}],self.now)
        self.assertEqual(out[0]['state'],'not_connected')
    def test_missing_temp_not_automatically_cool(self):
        pc={'status':'measured','cpu_pct':12,'ram_pct':49,'cpu_temp_c':None,'disk_free_gb':230,'critical_services':[]}
        result=agent.assess_pc(pc,{},[])
        self.assertIn('temp_unavailable',[x['code'] for x in result])
    def test_sustained_ram_pressure_warning(self):
        pc={'status':'measured','cpu_pct':12,'ram_pct':91,'cpu_temp_c':62,'disk_free_gb':230,'critical_services':[]}
        prev=[{'pc':{'ram_pct':90}},{'pc':{'ram_pct':93}}]
        result=agent.assess_pc(pc,{},prev)
        found=[x for x in result if x['code']=='ram_pressure'][0]
        self.assertEqual(found['severity'],'high')
        self.assertTrue(found['approval_required'])
    def test_critical_process_does_not_trigger_termination(self):
        pc={'status':'measured','cpu_pct':96,'ram_pct':91,'cpu_temp_c':90,'disk_free_gb':12,
            'critical_services':[{'name':'surveillance_client.exe','status':'process_seen'}]}
        result=agent.assess_pc(pc,{},[])
        self.assertTrue(all('kill' not in x['recommendation'].lower() for x in result))
    def test_no_sync_with_short_key(self):
        with self.assertRaises(ValueError):agent.sign_snapshot({'kind':'pc_task_snapshot'},'short')
    def test_signing_payload(self):
        val=agent.sign_snapshot({'kind':'pc_task_snapshot','value':1},'x'*40)
        self.assertEqual(len(val['signature']),64)
    def test_correlation_not_causation(self):
        pc={'ram_pct':92}
        jobs=[{'job_id':'camera_analytics','name':'Camera analytics heartbeat','state':'overdue'}]
        result=agent.correlate(pc,jobs,[])
        self.assertIn('not proof',result[0]['assessment'])

if __name__=='__main__':unittest.main()
