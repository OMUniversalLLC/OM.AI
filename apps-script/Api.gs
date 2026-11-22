/** OM AI server API. All client calls enforce Google identity + store permissions. */
function doGet() {
  try { omAuth_(); }
  catch (e) {
    return HtmlService.createHtmlOutput('<!doctype html><html><meta name="viewport" content="width=device-width,initial-scale=1"><body style="font-family:system-ui;background:#0c1629;color:#fff;padding:10vh 6vw"><h1>OM AI · Access unavailable</h1><p>'+omEscape_(e.message)+'</p><p>Sign in with an approved Google account and make sure that account can open the private OM AI Sheet.</p></body></html>').setTitle('OM AI — Access');
  }
  var html=HtmlService.createTemplateFromFile('Index');
  return html.evaluate().setTitle('OM AI — Operations Intelligence').addMetaTag('viewport','width=device-width,initial-scale=1');
}
function include(name) { return HtmlService.createHtmlOutputFromFile(name).getContent(); }
function omEscape_(text) { return String(text).replace(/[&<>"']/g,function(x){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x];}); }

function getOmAiDashboard(storeId) {
  var user=omAuth_();
  var stores=omRead_('Stores').filter(function(s) {
    return String(s.active).toLowerCase()==='yes' && (user.role==='Admin'||user.storeList.indexOf(s.store_id)>=0);
  });
  if (!stores.length) throw new Error('No stores are assigned to this account.');
  storeId=storeId||stores[0].store_id;
  var store=omStoreAccess_(user,storeId,false);
  var sales=omForStore_(omRead_('Sales',12000),storeId).sort(function(a,b){return a.date.localeCompare(b.date);});
  var inventory=omForStore_(omRead_('Inventory',3000),storeId);
  var vendors=omForStore_(omRead_('Vendors',2500),storeId);
  var tasks=omForStore_(omRead_('Tasks',2500),storeId);
  var expenses=omForStore_(omRead_('Expenses',2500),storeId);
  var operations=omForStore_(omRead_('Operations',2500),storeId);
  var compliance=omForStore_(omRead_('Compliance',1500),storeId);
  var incidents=omForStore_(omRead_('Incidents',1800),storeId);
  var events=omForStore_(omRead_('ExternalEvents',2000),storeId);
  var signals=omForStore_(omRead_('Signals',2000),storeId).sort(function(a,b){return String(b.observed_at).localeCompare(String(a.observed_at));});
  var summary=omSummary_(sales,vendors,inventory,tasks,events,incidents,expenses,compliance);
  var alerts=omAlerts_(storeId,sales,vendors,inventory,tasks,incidents,events,signals,compliance);
  var forecast=omForecast_(sales,omToday_(),7);
  var impacts=omImpacts_(storeId,signals,events,summary);
  var wifi=omWifiPayload_(storeId);
  var pcIntelligence=omPcPayload_(storeId);
  if(user.role==='Viewer'){pcIntelligence.pc.processes=[];pcIntelligence.pc.critical_services=[];pcIntelligence.reviews=[];}
  // Viewer role cannot receive device IP/MAC operational identifiers.
  if(user.role==='Viewer')wifi.devices=wifi.devices.map(function(d){return Object.assign({},d,{ip_address:'',mac_masked:''});});
  if(wifi.configured&&!wifi.fresh){alerts.unshift({severity:'medium',title:'OM WiFi monitor is stale',
    details:'No network agent update within 15 minutes; device status is unknown.',source:'OM WiFi',store_id:storeId});}
  if(wifi.fresh){
    wifi.devices.filter(function(x){return x.critical==='Yes'&&x.status==='suspected_offline';}).forEach(function(x){
      alerts.unshift({severity:'high',title:'Network equipment needs review: '+x.label,
        details:'Two or more TCP tests failed. This is not confirmation of power loss or NVR recording failure.',source:'OM WiFi',store_id:storeId});
    });
    wifi.cameras.filter(function(x){return x.status==='probe_failed';}).forEach(function(x){
      alerts.push({severity:'medium',title:'Camera stream check failed: '+x.name,
        details:'RTSP probe did not complete; verify channel and recording on NVR.',source:'OM WiFi',store_id:storeId});
    });
  }
  if(pcIntelligence.pcConfigured&&!pcIntelligence.pcFresh)alerts.unshift({severity:'medium',title:'OM PC Intelligence is stale',details:'No recent store PC heartbeat; live machine health is unknown.',source:'OM PC',store_id:storeId});
  if(pcIntelligence.pcFresh){
    pcIntelligence.alerts.slice(0,8).forEach(function(x){if(Date.now()-Date.parse(x.observed_at)<1800000)alerts.push({severity:x.severity,title:x.title,details:x.detail,source:'OM PC',store_id:storeId});});
  }
  if(pcIntelligence.fresh){
    pcIntelligence.jobs.filter(function(j){return j.state==='failed'||j.state==='overdue';}).slice(0,8).forEach(function(j){alerts.push({severity:'medium',title:'Automated task: '+j.name,details:j.state+' · '+j.next_action,source:'OM Orchestrator',store_id:storeId});});
  }
  var props=omProps_();
  return {
    user:{email:user.email,name:user.name,role:user.role}, stores:stores, store:store,
    summary:summary, alerts:alerts, forecast:forecast, impacts:impacts,
    sales:sales.slice(-150).reverse(), inventory:inventory.slice(-120), vendors:vendors.slice(-120).reverse(),
    expenses:expenses.slice(-180).reverse(),operations:operations.slice(-180).reverse(),compliance:compliance.slice(-120).reverse(),
    tasks:tasks.slice(-180).reverse(), incidents:incidents.slice(-100).reverse(), events:events.slice(-100).reverse(), signals:signals.slice(0,100),
    integration:{weather:'NWS enabled for located US stores',traffic:props.getProperty('TOMTOM_API_KEY')?'configured':'API key not configured',
      news:'Google News RSS (best-effort)',ai:props.getProperty('GEMINI_API_KEY')?'configured':'API key not configured',
      openai:props.getProperty('OPENAI_API_KEY')&&props.getProperty('OPENAI_MODEL')?'configured':'API key/model not configured'},
    fuelSources:omFuelPayload_(storeId),
    cameras:omCameraPayload_(storeId),
    wifi:wifi,
    pcIntelligence:pcIntelligence,
    timestamp:omNow_(),isDemo:false,databaseUrl:'https://docs.google.com/spreadsheets/d/'+props.getProperty('OM_AI_SHEET_ID')+'/edit'
  };
}

function saveOmAiRecord(kind,data) {
  data=data||{};
  var user=omAuth_(), storeId=String(data.store_id||'');
  omStoreAccess_(user,storeId,true);
  var now=omNow_(), record=null, tab='';
  var positive=function(key){var n=Number(data[key]);if(!isFinite(n)||n<0||n>100000000)throw new Error('Invalid '+key+'.');return n;};
  if(kind==='sale') {
    tab='Sales';
    record={id:omUid_('SAL'),date:omDate_(data.date),store_id:storeId,inside_sales:positive('inside_sales'),customers:positive('customers'),
      transactions:positive('transactions'),fuel_gallons:positive('fuel_gallons'),fuel_sales:positive('fuel_sales'),lottery_sales:positive('lottery_sales'),
      car_wash_sales:positive('car_wash_sales'),notes:omClean_(data.notes,500),created_at:now};
    if (omRead_('Sales').some(function(x){return x.date===record.date && x.store_id===storeId;})) throw new Error('A sale record already exists for this store/date. Edit it in Sheets instead of duplicating it.');
  } else if (kind==='task') {
    tab='Tasks';
    if(!String(data.title||'').trim()) throw new Error('Task title is required.');
    record={id:omUid_('TSK'),store_id:storeId,title:omClean_(data.title,160),assigned_to:omClean_(data.assigned_to,100),
      due_date:data.due_date?omDate_(data.due_date):'',priority:omEnum_(data.priority,['Low','Medium','High'],'Medium'),
      status:'Open',notes:omClean_(data.notes,650),created_at:now,updated_at:now};
  } else if (kind==='incident') {
    tab='Incidents';
    if(!String(data.description||'').trim()) throw new Error('Incident description is required.');
    record={id:omUid_('INC'),date:omDate_(data.date),store_id:storeId,category:omClean_(data.category,70),
      severity:omEnum_(data.severity,['Low','Medium','High'],'Medium'),description:omClean_(data.description,1000),
      status:'Open',created_at:now};
  } else if(kind==='vendor') {
    tab='Vendors';
    if(!String(data.vendor||'').trim()) throw new Error('Vendor name is required.');
    record={id:omUid_('VEN'),date:omDate_(data.date),store_id:storeId,vendor:omClean_(data.vendor,120),invoice_number:omClean_(data.invoice_number,50),
      invoice_total:positive('invoice_total'),audit_total:positive('audit_total'),discount:positive('discount'),credit:positive('credit'),
      status:omEnum_(data.status,['Open','Followed up','Working','Resolved'],'Open'),notes:omClean_(data.notes,600),created_at:now};
  } else if(kind==='expense') {
    tab='Expenses';record={id:omUid_('EXP'),date:omDate_(data.date),store_id:storeId,category:omClean_(data.category,70),vendor:omClean_(data.vendor,120),amount:positive('amount'),payment_method:omClean_(data.payment_method,50),notes:omClean_(data.notes,500),created_at:now};
  } else if(kind==='metric') {
    tab='Operations';if(!String(data.metric||'').trim())throw new Error('Metric name is required.');
    record={id:omUid_('MET'),date:omDate_(data.date),store_id:storeId,area:omClean_(data.area,70),metric:omClean_(data.metric,100),value:positive('value'),unit:omClean_(data.unit,35),notes:omClean_(data.notes,500),created_at:now};
  } else if(kind==='compliance') {
    tab='Compliance';if(!String(data.name||'').trim())throw new Error('Compliance item is required.');
    record={id:omUid_('COM'),store_id:storeId,name:omClean_(data.name,180),category:omClean_(data.category,70),due_date:omDate_(data.due_date),owner:omClean_(data.owner,100),status:'Open',notes:omClean_(data.notes,500),created_at:now,updated_at:now};
  } else if(kind==='inventory') {
    tab='Inventory';
    if(!String(data.item_name||'').trim()) throw new Error('Item name is required.');
    record={id:omUid_('INV'),store_id:storeId,sku:omClean_(data.sku,45),item_name:omClean_(data.item_name,160),department:omClean_(data.department,60),
      on_hand:positive('on_hand'),reorder_point:positive('reorder_point'),unit_cost:positive('unit_cost'),retail_price:positive('retail_price'),updated_at:now};
  } else if(kind==='event') {
    tab='ExternalEvents';
    if(!String(data.title||'').trim()) throw new Error('Event title is required.');
    record={id:omUid_('EVT'),store_id:storeId,event_date:omDate_(data.event_date),category:omClean_(data.category,60),title:omClean_(data.title,200),
      description:omClean_(data.description,1000),severity:omEnum_(data.severity,['Low','Medium','High'],'Medium'),source_url:omUrl_(data.source_url),
      start_date:data.start_date?omDate_(data.start_date):'',end_date:data.end_date?omDate_(data.end_date):'',status:omEnum_(data.status,['Planned','Active','Closed'],'Planned'),created_at:now};
  } else throw new Error('Unsupported record type.');
  return omLock_(function(){omAppend_(tab,record);omLog_('create:'+tab,storeId,record.id,record.title||record.item_name||record.vendor||record.date);return {ok:true,id:record.id};});
}

function setOmAiTaskStatus(storeId,taskId,newStatus) {
  var user=omAuth_();omStoreAccess_(user,storeId,true);
  var allowed=['Open','In Progress','Waiting','Completed','Cancelled'];
  if (allowed.indexOf(newStatus)<0) throw new Error('Invalid task status.');
  var task=omRead_('Tasks').filter(function(x){return x.id===taskId && x.store_id===storeId;})[0];
  if (!task) throw new Error('Task not found in this store.');
  return omLock_(function(){omPatch_('Tasks',taskId,{status:newStatus,updated_at:omNow_()});omLog_('task_status',storeId,taskId,newStatus);return {ok:true};});
}

function setOmAiComplianceStatus(storeId,id,status) {
 var user=omAuth_();omStoreAccess_(user,storeId,true);
 if(['Open','In Progress','Completed','Cancelled'].indexOf(status)<0)throw new Error('Invalid status.');
 var found=omRead_('Compliance').some(function(x){return x.store_id===storeId && x.id===id;});
 if(!found)throw new Error('Compliance record not found.');
 return omLock_(function(){omPatch_('Compliance',id,{status:status,updated_at:omNow_()});omLog_('compliance_status',storeId,id,status);return {ok:true};});
}

/** Import ONLY a normalized flat table with matching header names; never attempt to parse mixed-format original sheets automatically. */
function importNormalizedSalesFromSheet(sourceSpreadsheetId,sourceTabName) {
  omOwner_();
  var sh=SpreadsheetApp.openById(String(sourceSpreadsheetId)).getSheetByName(String(sourceTabName));
  if(!sh)throw new Error('Source tab not found.');
  var v=sh.getDataRange().getValues();if(v.length<2)return {imported:0,skipped:0};
  var header=v[0].map(function(x){return String(x).toLowerCase().trim();});
  ['date','store_id','inside_sales','customers'].forEach(function(h){if(header.indexOf(h)<0)throw new Error('Missing required header: '+h);});
  var existing={};omRead_('Sales').forEach(function(x){existing[x.store_id+'|'+x.date]=true;});
  var stores=omRead_('Stores').map(function(x){return x.store_id;});
  var rows=[],skipped=0;
  v.slice(1).forEach(function(raw){
    var r={};header.forEach(function(h,i){r[h]=raw[i];});
    var day = r.date instanceof Date ? Utilities.formatDate(r.date,'America/New_York','yyyy-MM-dd') : String(r.date||'').slice(0,10);
    var key=r.store_id+'|'+day;
    if(!day||stores.indexOf(r.store_id)<0||existing[key]){skipped++;return;}
    try{omDate_(day);}catch(e){skipped++;return;}
    var out={id:omUid_('IMP'),date:day,store_id:r.store_id,created_at:omNow_(),notes:omClean_(r.notes||'Imported',200)};
    ['inside_sales','customers','transactions','fuel_gallons','fuel_sales','lottery_sales','car_wash_sales'].forEach(function(k){out[k]=Math.max(0,omNum_(r[k]));});
    rows.push(OM_SCHEMA.Sales.map(function(k){return out[k]==null?'':out[k];}));existing[key]=true;
  });
  if(rows.length)omLock_(function(){var t=omDb_().getSheetByName('Sales');t.getRange(t.getLastRow()+1,1,rows.length,OM_SCHEMA.Sales.length).setValues(rows);omLog_('bulk_import','', '',rows.length+' records from '+sourceTabName);});
  return {imported:rows.length,skipped:skipped};
}
