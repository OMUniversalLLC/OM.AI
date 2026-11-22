"""Build a strictly illustrative, local HTML preview (no private data)."""
from pathlib import Path
import json, random
from datetime import date, timedelta
root=Path(__file__).resolve().parents[1]
css=(root/'apps-script/Styles.html').read_text()
js=(root/'apps-script/Client.html').read_text()
r=random.Random(23)
today=date(2026,11,19)
sales=[]
for n in range(44,-1,-1):
    day=today-timedelta(days=n)
    v=round(3800+((day.weekday()+3)%7)*95+r.randrange(-300,350),2)
    sales.append({'date':str(day),'store_id':'QUICKC','inside_sales':v,'customers':r.randrange(190,280),'transactions':r.randrange(195,320),'fuel_gallons':round(r.randrange(1400,2700)/10,1),'fuel_sales':round(r.randrange(3500,6000),2),'lottery_sales':round(r.randrange(400,900),2),'car_wash_sales':0})
last=sales[-1]; avg=sum(x['inside_sales'] for x in sales[-7:])/7; prev=sum(x['inside_sales'] for x in sales[-14:-7])/7
series=[{'date':x['date'],'sales':x['inside_sales'],'customers':x['customers'],'fuel':x['fuel_sales']} for x in sales]
fc=[]
for n in range(7):
    d=today+timedelta(days=n)
    matches=[x['inside_sales'] for x in sales if date.fromisoformat(x['date']).weekday()==d.weekday()][-8:]
    weighted=sum(x*(i+1) for i,x in enumerate(matches))/sum(range(1,len(matches)+1))
    fc.append({'date':str(d),'expected':round(weighted,2),'lower':round(weighted*.85,2),'upper':round(weighted*1.15,2),'sample':len(matches)})
store={'store_id':'QUICKC','name':'Quick-C SUNOCO — Plant City','address':'','latitude':'','longitude':'','timezone':'America/New_York','active':'Yes'}
other=[{'store_id':x,'name':n,'address':'Configure store address','latitude':'','longitude':'','timezone':'America/New_York','active':'Yes'} for x,n in [('INVERNESS','Demo Store 2'),('VAPESTORE','Demo Store 3')]]
signals=[{'store_id':'QUICKC','source':'NWS','kind':'weather_forecast','observed_at':'DEMO ONLY','title':'Illustrative forecast: Cloudy','details':'Example forecast for demonstration only. Not a live weather reading.','source_url':'https://www.weather.gov/'},
{'store_id':'QUICKC','source':'TomTom','kind':'traffic_flow','observed_at':'DEMO ONLY','title':'Illustrative nearby road speed','value':43,'unit':'km/h','details':'Example traffic snapshot only; not measured.','source_url':'https://www.tomtom.com/traffic-index/'},
{'store_id':'QUICKC','source':'Google News RSS','kind':'news_mention','observed_at':'DEMO ONLY','title':'Example construction article title','details':'Illustrative placeholder; check FDOT for confirmed roadwork.','source_url':'https://fl511.com/'}]
alerts=[{'severity':'high','title':'Example low-stock item','details':'12 left · Reorder point 15','source':'Inventory','store_id':'QUICKC'}, {'severity':'medium','title':'Example vendor audit variance','details':'Net expected and audit do not match','source':'Vendor audit','store_id':'QUICKC'}, {'severity':'info','title':'Review construction route','details':'Sample alert: check official road projects','source':'External event','store_id':'QUICKC'}]
inventory=[{'sku':'DEMO-01','item_name':'Example Energy Drink','department':'Energy','on_hand':12,'reorder_point':15,'unit_cost':1.5,'retail_price':3.49}, {'sku':'DEMO-02','item_name':'Example Snack','department':'Snacks','on_hand':60,'reorder_point':20,'unit_cost':.65,'retail_price':1.99}]
tasks=[{'id':'DEMO-T1','title':'Check road construction detour','assigned_to':'Manager','due_date':'2026-11-20','priority':'High','status':'In Progress','notes':'Illustrative task'},{'id':'DEMO-T2','title':'Reconcile sample vendor discount','assigned_to':'Back office','due_date':'2026-11-22','priority':'Medium','status':'Open','notes':'Illustrative task'}]
vendors=[{'date':'2026-11-17','vendor':'Example Distributor','invoice_number':'DEMO-001','invoice_total':1030,'audit_total':990,'discount':20,'credit':0,'status':'Working'}]
summary={'latest_date':last['date'],'latest_sales':last['inside_sales'],'latest_customers':last['customers'],'latest_avg_ticket':round(last['inside_sales']/last['transactions'],2), 'sales_last7':round(sum(x['inside_sales'] for x in sales[-7:]),2),'sales_prev7':round(sum(x['inside_sales'] for x in sales[-14:-7]),2),'change_pct':round((avg-prev)/prev*100,1),'sales_days':len(sales),'fuel_gallons_last7':round(sum(x['fuel_gallons'] for x in sales[-7:]),1),'lottery_last7':round(sum(x['lottery_sales'] for x in sales[-7:]),2),'low_stock_count':1,'open_tasks':2,'overdue_tasks':0,'open_incidents':1,'vendor_variance':20,'expenses_last7':354.60,'compliance_due':1,'upcoming_events':1,'series':series}
data={'user':{'email':'demo@example.com','name':'Demo Manager','role':'Admin'},'stores':[store]+other,'store':store,'summary':summary,'alerts':alerts,'impacts':[{'type':'Traffic','level':'medium','title':'Example roadway slowdown','evidence':'Illustrative only: no measured traffic data.','action':'Verify live conditions on FL511.','source':'Demo','verified':False},{'type':'Inventory','level':'medium','title':'One sample item below reorder point','evidence':'Invented demo inventory.','action':'Check physical stock.','source':'Demo','verified':True}],'forecast':{'status':'baseline','method':'Recency-weighted same-weekday average','required':14,'available':45,'points':fc,'note':'Demonstration only: figures and bands are fictional.'},'sales':list(reversed(sales)),'inventory':inventory,'vendors':vendors,'expenses':[{'date':'2026-11-18','category':'Maintenance','vendor':'Demo Supplier','payment_method':'EFT','amount':354.60,'notes':'Illustrative'}],'operations':[{'date':'2026-11-18','area':'ATM','metric':'Example withdrawal count','value':56,'unit':'transactions','notes':'Illustrative'}],'compliance':[{'id':'DEMO-C1','due_date':'2026-11-26','name':'Example permit renewal','category':'Tobacco','owner':'Manager','status':'Open','notes':'Example only'}],'tasks':tasks,'incidents':[{'category':'Equipment','date':'2026-11-18','severity':'Medium','status':'Open','description':'Example freezer maintenance ticket, not an actual store incident.'}], 'events':[{'title':'Example roadwork notice','description':'Illustrative event; not verified.','start_date':'2026-11-19','status':'Planned'}],'signals':signals,'integration':{'weather':'NWS example','traffic':'Demo only; API key required for live traffic','news':'Google News RSS demo','ai':'API key not configured'},'timestamp':'DEMO ONLY — illustrative','isDemo':True,'databaseUrl':'https://docs.google.com/spreadsheets/'}
data['fuelSources']={'sources':[
{'source_id':'AAA','name':'AAA market averages','url':'https://gasprices.aaa.com/?state=FL','purpose':'Daily Florida and Hillsborough average prices by grade','capture_mode':'Manual verified entry / approved feed','schedule':'Daily'},
{'source_id':'GasBuddy','name':'GasBuddy competitor prices','url':'https://www.gasbuddy.com/home','purpose':'Nearby stations, posted prices, and reported timestamps','capture_mode':'Manual verified entry / licensed data','schedule':'Daily'},
{'source_id':'MostEdge','name':'MostEdge store fuel report','url':'https://www.mostedge.com/','purpose':'Authorized store fuel deliveries, retail prices, costs and tank reconciliation','capture_mode':'Authorized export / manual entry','schedule':'Daily'}],
'latest':{'AAA':{'count':0,'last_seen':''},'GasBuddy':{'count':0,'last_seen':''},'MostEdge':{'count':0,'last_seen':''}},
'observations':[], 'reports':[], 'tasks':[
{'id':'DEMO-F1','store_id':'QUICKC','source_id':'AAA','task_date':'2026-11-19','task':'Capture Florida and county averages by grade','status':'Pending','assigned_to':'Fuel manager','due_date':'2026-11-19'},
{'id':'DEMO-F2','store_id':'QUICKC','source_id':'GasBuddy','task_date':'2026-11-19','task':'Verify nearby station prices and timestamps','status':'Pending','assigned_to':'Fuel manager','due_date':'2026-11-19'},
{'id':'DEMO-F3','store_id':'QUICKC','source_id':'MostEdge','task_date':'2026-11-19','task':'Import authorized daily fuel report and reconcile','status':'Pending','assigned_to':'Back office','due_date':'2026-11-19'}],
'freshness_note':'Demonstration only; no provider extraction or real prices.'}
# Camera module: illustrative activity records, never a representation of connected streams.
cam_plan=[(c['id'],c['name'],c['role']) for c in json.loads((root/'surveillance/cameras.json').read_text())['cameras']]
cam_metrics={}
cam_hourly=[]
cam_cards=[{'camera_id':i,'name':name,'role':role,'observer':'Unassigned',
 'task':'Verify camera stream, view, recording, zone and AI event before enabling',
 'status':'not_connected','today_count':0,'last_seen':'','secure_view_url':''}
 for i,name,role in cam_plan]
cam_checks=[{'id':f'DEMO-{i}','camera_id':i,'assigned_to':'Unassigned',
 'task':'Verify NVR channel and save test event', 'status':'Open'} for i,_,_ in cam_plan]
data['cameras']={'date':str(today),'hasData':False,'metrics':cam_metrics,'hourly':cam_hourly,
 'cameras':cam_cards,'checks':cam_checks,'cameraCount':14,'monitoredOnline':0,
 'notes':['The camera tiles illustrate a sample layout.',
 'Camera coverage depends on the local installation.',
 'All analytics roles are disabled pending real tests and validation.']}
# WiFi/Network: all values explicitly DEMO ONLY. No live network check occurs in preview.
data['wifi']={'configured':True,'fresh':True,'last_checked':'DEMO ONLY — not actual connection check',
 'pc_wifi_state':'connected','pc_wifi_ssid':'DEMO-Store-WiFi','pc_wifi_signal':71,'pc_wifi_receive_mbps':144.4,'pc_wifi_transmit_mbps':144.4,
 'router_export_state':'not_configured',
 'devices':[
 {'device_id':'NVR','label':'Example iLink recorder','device_type':'nvr','connection':'wired_or_unknown','ip_address':'192.0.2.10','status':'reachable','method':'tcp_known_target','evidence':'Fictional TCP test success','critical':'Yes'},
 {'device_id':'STORE_ROUTER','label':'Example router','device_type':'router','connection':'unknown','ip_address':'—','status':'not_configured','method':'tcp_known_target','evidence':'No router details provided','critical':'Yes'},
 {'device_id':'OBS-EXAMPLE','label':'Unrecognized network neighbor','device_type':'unknown','connection':'unknown','ip_address':'192.0.2.42','status':'observed_in_cache','method':'neighbor_cache','evidence':'Fictional ARP entry, not proof of association','critical':'No'}],
 'cameras':[{'camera_id':c['camera_id'],'name':c['name'],'status':'not_configured','details':'Awaiting channel check; demo only'} for c in cam_cards],
 'events':[{'device_id':'NVR','severity':'info','details':'Example restored connection after a failed check','occurred_at':'DEMO ONLY'}],
 'total_devices':3,'reachable_devices':1,'suspected_offline':0,'verified_streams':0}
# OM PC / Orchestrator strictly illustrative. No real process, camera or provider values.
data['pcIntelligence']={
 'configured':True,'fresh':True,'updated_at':'DEMO ONLY — no live PC telemetry',
 'pc':{'status':'measured','cpu_pct':38.2,'ram_pct':67.1,'ram_used_gb':8.2,'ram_available_gb':4.2,
       'disk_pct':61,'disk_free_gb':231.6,'gpu_pct':None,'cpu_temp_c':None,'gpu_temp_c':None,
       'sensor_source':'not_configured',
       'processes':[{'name':'surveillance_client.exe','count':1,'ram_mb':642.3,'cpu_pct':8.2,'protected':True},
                    {'name':'chrome.exe','count':9,'ram_mb':1634.7,'cpu_pct':6.1,'protected':False},
                    {'name':'python.exe','count':2,'ram_mb':301.2,'cpu_pct':4.0,'protected':False}]},
 'jobs':[
  {'job_id':'gasbuddy_daily','name':'GasBuddy local price verification','provider':'GasBuddy','owner':'Fuel team','state':'needs_evidence','last_run':'DEMO ONLY','next_action':'Attach station price timestamps and verified screenshots'},
  {'job_id':'aaa_daily','name':'AAA area average price verification','provider':'AAA','owner':'Fuel team','state':'healthy','last_run':'DEMO ONLY','evidence_ref':'https://gasprices.aaa.com/','next_action':'No action required'},
  {'job_id':'mostedge_daily','name':'MostEdge authorized store report','provider':'MostEdge','owner':'Back office','state':'overdue','last_run':'DEMO ONLY','next_action':'Check export permissions and source freshness'},
  {'job_id':'nvr_record_check','name':'NVR recording and playback check','provider':'Store IT','owner':'Surveillance lead','state':'not_connected','last_run':None,'next_action':'Validate playback'},
  {'job_id':'camera_analytics','name':'Camera analytics heartbeat','provider':'Store PC','owner':'Store IT','state':'running','last_run':'DEMO ONLY','next_action':'Wait for job result'},
  {'job_id':'wifi_health','name':'Wi-Fi device heartbeat','provider':'Store PC','owner':'Store IT','state':'healthy','last_run':'DEMO ONLY','next_action':'No action required'},
  {'job_id':'weather_refresh','name':'NWS weather alert ingestion','provider':'NWS','owner':'OM Radar','state':'healthy','last_run':'DEMO ONLY','next_action':'No action required'},
  {'job_id':'news_review','name':'News impact verification','provider':'News feeds','owner':'Management','state':'needs_review','last_run':'DEMO ONLY','next_action':'Review article quality'},
  {'job_id':'gemini_report','name':'Optional Gemini report quality check','provider':'Gemini API','owner':'Back office','state':'not_connected','last_run':None,'next_action':'Configure authorized key'},
  {'job_id':'openai_report','name':'Optional OpenAI API report quality check','provider':'OpenAI API','owner':'Back office','state':'not_connected','last_run':None,'next_action':'Configure authorized key'}],
 'alerts':[{'severity':'info','title':'CPU temperature not measured','detail':'No validated sensor input in demo','next_action':'Configure a trusted local sensor export'}],
 'reviews':[]}
html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OM AI — Preview (Demo only)</title>'''+css+'''</head><body><div id="app" class="loading-app"><div class="spinner"></div><p>Loading illustrative preview…</p></div><div id="toast-host" aria-live="polite"></div><script>window.OMAI_DEMO=true;window.OMAI_DEMO_DATA='''+json.dumps(data).replace('<','\\u003c')+''';</script>'''+js+'''</body></html>'''
(root/'preview/OM-AI-preview.html').write_text(html)
print('Built preview:', root/'preview/OM-AI-preview.html',len(html),'bytes')
