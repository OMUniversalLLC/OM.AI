/** OM PC Intelligence + task proof-of-execution intake. PRIVATE aggregate telemetry only.
 * Set OM_PC_SYNC_SECRET (random >= 32 chars) in private Apps Script Properties.
 * NEVER publish these tables in GitHub Pages public snapshot.
 * This endpoint neither executes commands nor controls the store PC.
 */
var OM_PC_STATES_=['measured','unavailable'];
var OM_JOB_STATES_=['healthy','failed','overdue','not_connected','needs_review','needs_evidence','skipped','running'];
function omPcIngest_(env){
  var secret=omProps_().getProperty('OM_PC_SYNC_SECRET');
  if(!secret||secret.length<32)throw new Error('PC sync not configured');
  if(!env||env.kind!=='pc_task_snapshot'||typeof env.payload!=='string'||typeof env.signature!=='string'||env.payload.length>110000)throw new Error('Invalid PC envelope');
  var raw=Utilities.newBlob(Utilities.base64Decode(env.payload)).getDataAsString('UTF-8');
  var expected=Utilities.computeHmacSha256Signature(raw,secret).map(function(b){return ('0'+(b&255).toString(16)).slice(-2);}).join('');
  var offered=String(env.signature||'').toLowerCase(),delta=expected.length^offered.length;
  for(var i=0;i<Math.min(expected.length,offered.length);i++)delta|=expected.charCodeAt(i)^offered.charCodeAt(i);
  if(delta)throw new Error('PC signature invalid');
  var data=JSON.parse(raw);
  var storeId=String(data.store_id||'');
  if(data.kind!=='pc_task_snapshot'||storeId!=='QUICKC')throw new Error('Store mismatch');
  if(!isFinite(Date.parse(data.sent_at))||Math.abs(Date.now()-Date.parse(data.sent_at))>300000)throw new Error('PC report too old/future');
  if(!/^STORE-PC-[0-9]{2}$/.test(String(data.device_id||'')))throw new Error('Unexpected device identifier');
  if(!data.pc||!Array.isArray(data.jobs)||data.jobs.length>80||!Array.isArray(data.alerts)||data.alerts.length>40||
     !Array.isArray(data.insights)||data.insights.length>10)throw new Error('Malformed PC snapshot');
  var pc=data.pc;
  var bound=function(n,hi){if(n==null)return '';var v=Number(n);if(!isFinite(v)||v<0||v>hi)throw new Error('PC metric out of range');return v;};
  var stamp=String(data.sent_at);
  var row={device_id:data.device_id,store_id:storeId,updated_at:stamp,status:omEnum_(pc.status,OM_PC_STATES_,'unavailable'),
   cpu_pct:bound(pc.cpu_pct,100),ram_pct:bound(pc.ram_pct,100),ram_used_gb:bound(pc.ram_used_gb,999),
   ram_available_gb:bound(pc.ram_available_gb,999),disk_pct:bound(pc.disk_pct,100),disk_free_gb:bound(pc.disk_free_gb,30000),
   gpu_pct:bound(pc.gpu_pct,100),cpu_temp_c:bound(pc.cpu_temp_c,125),gpu_temp_c:bound(pc.gpu_temp_c,125),
   uptime_hours:bound(pc.uptime_hours,500000),sensor_source:omClean_(pc.sensor_source,60),
   process_note:omClean_(pc.note,180),processes_json:JSON.stringify((Array.isArray(pc.processes)?pc.processes:[]).slice(0,12).map(function(x){
    return {name:omClean_(x.name,65),count:bound(x.count,1000),ram_mb:bound(x.ram_mb,100000),
      cpu_pct:bound(x.cpu_pct,5000),protected:x.protected===true};
   })),critical_json:JSON.stringify((Array.isArray(pc.critical_services)?pc.critical_services:[]).slice(0,15).map(function(x){
    return {name:omClean_(x.name,65),status:omEnum_(x.status,['process_seen','not_seen'],'not_seen')};
   })),safety_note:'Advisory only. No remote process stops, service restarts, firmware updates or configuration changes.'};
  var jobs=data.jobs.map(function(j){
    if(!/^[A-Za-z][A-Za-z0-9_\-]{2,49}$/.test(String(j.job_id||'')))throw new Error('Bad job ID');
    var t=j.last_run==null?'':String(j.last_run);
    if(t&&!isFinite(Date.parse(t)))throw new Error('Invalid job timestamp');
    return {id:storeId+'|'+j.job_id,store_id:storeId,job_id:j.job_id,name:omClean_(j.name,90),
     provider:omClean_(j.provider,45),owner:omClean_(j.owner,60),state:omEnum_(j.state,OM_JOB_STATES_,'needs_review'),
     last_run:t,age_hours:bound(j.age_hours,8000),max_age_hours:bound(j.max_age_hours,8000),
     detail:omClean_(j.detail,180),next_action:omClean_(j.next_action,260),
     evidence_ref:omUrl_(j.evidence_ref),checked_at:stamp};
  });
  var alerts=data.alerts.map(function(a){
    return {id:'PC|'+storeId+'|'+data.device_id+'|'+omClean_(a.code,70)+'|'+stamp,
     store_id:storeId,device_id:data.device_id,observed_at:stamp,kind:omClean_(a.code,70),
     severity:omEnum_(a.severity,['info','medium','high'],'info'),title:omClean_(a.title,130),
     detail:omClean_(a.detail,240),next_action:omClean_(a.recommendation,350),
     approval_required:'Yes',source:'local_pc_agent'};
  });
  // Build then validate before changing Sheet. Ignore replay/older data.
  var previous=omRead_('PcStatus',100).filter(function(x){return x.device_id===data.device_id;})[0];
  if(previous&&Date.parse(previous.updated_at)>=Date.parse(stamp))return {ok:true,duplicate:true};
  var existingJobs={};omForStore_(omRead_('PcJobs',1000),storeId).forEach(function(j){existingJobs[j.id]=true;});
  var seenAlerts={};omForStore_(omRead_('PcAlerts',1800),storeId).forEach(function(a){seenAlerts[a.id]=true;});
  omLock_(function(){
    if(previous)omPatch_('PcStatus',data.device_id,row);else omAppend_('PcStatus',row);
    jobs.forEach(function(j){if(existingJobs[j.id])omPatch_('PcJobs',j.id,j);else omAppend_('PcJobs',j);});
    alerts.forEach(function(a){if(!seenAlerts[a.id])omAppend_('PcAlerts',a);});
  });
  return {ok:true,store_id:storeId,jobs:jobs.length,alerts:alerts.length};
}

function omPcPayload_(storeId){
 var pc=omForStore_(omRead_('PcStatus',100),storeId)[0]||{};
 var pcFresh=!!pc.updated_at&&isFinite(Date.parse(pc.updated_at))&&Date.now()-Date.parse(pc.updated_at)<900000;
 pc.processes=[];pc.critical_services=[];
 try{pc.processes=JSON.parse(pc.processes_json||'[]');pc.critical_services=JSON.parse(pc.critical_json||'[]');}catch(e){}
 var localJobs=omForStore_(omRead_('PcJobs',500),storeId).map(function(j){
   return Object.assign({},j,{state:pcFresh?j.state:'stale',origin:'pc'});
 });
 var serviceJobs=omForStore_(omRead_('ServiceJobs',400),storeId).map(function(j){
   var age=(Date.now()-Date.parse(j.last_run))/3600000;
   var state=!isFinite(age)||age<0?'stale':age>Number(j.max_age_hours||3)?'overdue':j.state;
   return Object.assign({},j,{state:state,origin:'server'});
 });
 var jobs=localJobs.concat(serviceJobs);
 var recentServer=serviceJobs.some(function(j){return j.state!=='stale'&&j.state!=='overdue'&&j.state!=='not_connected';});
 var alerts=omForStore_(omRead_('PcAlerts',500),storeId)
     .sort(function(a,b){return String(b.observed_at).localeCompare(String(a.observed_at));}).slice(0,35);
 var reviews=omForStore_(omRead_('JobReviews',200),storeId)
     .sort(function(a,b){return String(b.reviewed_at).localeCompare(String(a.reviewed_at));}).slice(0,50);
 return {configured:!!pc.updated_at||jobs.length>0,fresh:pcFresh||recentServer,
  pcConfigured:!!pc.updated_at,pcFresh:pcFresh,updated_at:pc.updated_at||'',
  pc:Object.assign({},pc,{status:pcFresh?(pc.status||'unavailable'):'stale'}), jobs:jobs,alerts:alerts,
  reviews:reviews,healthy:jobs.filter(function(x){return x.state==='healthy';}).length,
  unhealthy:jobs.filter(function(x){return ['overdue','failed','needs_evidence','needs_review'].indexOf(x.state)>=0;}).length,
  note:'Evidence and recent successful receipts are necessary but cannot guarantee every source result is correct.'};
}

/** Review only; NO Windows commands and NO automatic job completion. */
function reviewOmAiJob(storeId,jobId,decision,notes){
  var user=omAuth_();omStoreAccess_(user,storeId,true);
  if(user.role==='Viewer')throw new Error('Review permission denied');
  if(['Acknowledged','Investigating','Escalated','Verified'].indexOf(decision)<0)throw new Error('Invalid review decision');
  var known=omForStore_(omRead_('PcJobs',500),storeId).some(function(j){return j.job_id===jobId;});
  if(!known)throw new Error('Unknown job');
  var item={id:omUid_('JOBREVIEW'),store_id:storeId,job_id:jobId,decision:decision,
            reviewed_by:user.email,reviewed_at:omNow_(),notes:omClean_(notes,350)};
  return omLock_(function(){omAppend_('JobReviews',item);omLog_('pc_job_review',storeId,item.id,jobId+' / '+decision);return {ok:true,id:item.id};});
}
