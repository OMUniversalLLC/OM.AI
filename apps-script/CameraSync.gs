/** OM AI Camera Analytics: PRIVATE aggregate counters only.
 * Public Apps Script doPost is a minimal signed intake; never send raw CCTV.
 * Set a 32+ character OM_CAMERA_SYNC_SECRET in Script Properties, not the Sheet.
 */
var OM_CAMERA_ROLE_PLAN_ = Array.from({length: 14}, function(_, index) {
  var number = String(index + 1).padStart(2, '0');
  return ['CAM' + number, 'Camera ' + number, 'activity_only',
    'Verify the channel, recording, and analytics before enabling.'];
});

function omPrivateCameraPlan_() {
  var raw = omProps_().getProperty('OM_PRIVATE_CAMERA_PLAN');
  if (!raw) return null;
  var rows = JSON.parse(raw);
  if (!Array.isArray(rows) || !rows.length || rows.length > 14) {
    throw new Error('Invalid private camera plan');
  }
  var seen = {};
  rows.forEach(function(row) {
    if (!Array.isArray(row) || row.length !== 4 || !row.every(function(value) {
      return typeof value === 'string' && value.trim() && value.length <= 300;
    }) || !/^CAM(?:0[1-9]|1[0-4])$/.test(row[0]) || seen[row[0]] || row[2] !== 'activity_only') {
      throw new Error('Invalid private camera plan row');
    }
    seen[row[0]] = true;
  });
  return rows;
}

var OM_CAMERA_METRICS_ = ['vehicle_entry','vehicle_exit','road_vehicle','pump_dwell','store_door_entry',
 'carwash_entry','carwash_exit','delivery_vehicle','fuel_transaction','carwash_paid','carwash_controller_cycle','counter_wait_alert'];

function omSeedCameras_() {
  var existing=omRead_('CameraConfig');
  var ids={};existing.forEach(function(r){ ids[r.store_id+'|'+r.camera_id]=true; });
  (omPrivateCameraPlan_() || OM_CAMERA_ROLE_PLAN_).forEach(function(c){
    if (!ids['QUICKC|'+c[0]]) omAppend_('CameraConfig',{
      camera_id:c[0],store_id:'QUICKC',name:c[1],role:c[2],observer:'Unassigned',
      task:c[3],status:'not_connected',last_seen:'',secure_view_url:'',notes:'Camera inventory; analytics disabled. Verify stream-to-camera mapping, view angle, recording and detection event before enabling.'
    });
  });
}


/** One-time owner-only correction for any previously seeded hypothetical camera names.
 * Requires an explicit confirmation. Does NOT enable analytics or video streaming.
 * Review role/task edits before running because names/roles/tasks are replaced.
 */
function omAlignCameraNamesToActualNvr(confirmation) {
  omOwner_();
  if (confirmation !== 'REPLACE_HYPOTHETICAL_CAMERA_PLAN') throw new Error('Confirmation phrase required');
  var plan = omPrivateCameraPlan_();
  if (!plan) throw new Error('Set OM_PRIVATE_CAMERA_PLAN before aligning names');
  var existing = omForStore_(omRead_('CameraConfig'), 'QUICKC');
  var byId = {}; existing.forEach(function(c){byId[c.camera_id] = c;});
  return omLock_(function(){
    var count=0;
    plan.forEach(function(c){
      if (byId[c[0]]) {
        omPatch_('CameraConfig',c[0],{
          name:c[1],role:'activity_only',task:c[3],status:'not_connected',last_seen:'',
          secure_view_url:'',notes:'Imported NVR inventory — analytics deliberately disabled until validated.'
        });
      } else {
        omAppend_('CameraConfig',{
          camera_id:c[0],store_id:'QUICKC',name:c[1],role:'activity_only',observer:'Unassigned',
          task:c[3],status:'not_connected',last_seen:'',secure_view_url:'',
          notes:'Imported NVR inventory — analytics deliberately disabled until validated.'
        });
      }
      count++;
    });
    omLog_('camera_inventory_alignment','QUICKC',String(count),'Private NVR names aligned; analytics not enabled');
    return {ok:true,cameras:count,live_cameras_connected:0};
  });
}

function omCameraPayload_(storeId) {
  var cams=omForStore_(omRead_('CameraConfig',600),storeId);
  var rows=omForStore_(omRead_('CameraHour',15000),storeId);
  var store=omRead_('Stores').filter(function(s){return s.store_id===storeId;})[0]||{};
  var tz=String(store.timezone||'America/New_York');
  var today=Utilities.formatDate(new Date(),tz,'yyyy-MM-dd');
  var metrics={};var perCamera={};var hourly={};var recordsToday=0;
  rows.forEach(function(r){
    if(!/^\d{4}-\d{2}-\d{2}T/.test(String(r.hour_bucket)))return;
    var local;
    try{local=Utilities.formatDate(new Date(String(r.hour_bucket)),tz,'yyyy-MM-dd');}
    catch(e){return;}
    if(local!==today)return;
    var kind=String(r.metric),count=Math.max(0,Number(r.count)||0);
    metrics[kind]=(metrics[kind]||0)+count;
    perCamera[r.camera_id]=(perCamera[r.camera_id]||0)+count;
    var hour=Utilities.formatDate(new Date(String(r.hour_bucket)),tz,'HH:00');
    if(!hourly[hour])hourly[hour]={hour:hour,vehicles:0,road:0,store:0,pump:0,wash:0};
    if(kind==='vehicle_entry')hourly[hour].vehicles+=count;
    if(kind==='road_vehicle')hourly[hour].road+=count;
    if(kind==='store_door_entry')hourly[hour].store+=count;
    if(kind==='pump_dwell')hourly[hour].pump+=count;
    if(kind==='carwash_entry')hourly[hour].wash+=count;
    recordsToday++;
  });
  var hasRecords=recordsToday>0;
  var pending=omForStore_(omRead_('CameraChecks',1400),storeId).filter(function(x){return x.check_date===today;});
  return {date:today,hasData:hasRecords,
    metrics:metrics, hourly:Object.keys(hourly).sort().map(function(h){return hourly[h];}),
    cameras:cams.map(function(c){
      var status=c.status;
      if(status==='online'&&(!c.last_seen||(Date.now()-new Date(c.last_seen).getTime())>150000))status='stale';
      return Object.assign({},c,{status:status,today_count:perCamera[c.camera_id]||0});
    }),
    checks:pending, notes:[
      'Vehicle arrivals are camera observations; no fuel purchase is implied.',
      'Pump dwell counts are vehicles present near pumps, not verified fuel transactions.',
      'Store entrance counts people; do not infer vehicle-to-store conversion from different cameras.',
      'Paid washes require POS data; completed wash cycles require car-wash controller records.',
      'No camera heartbeat means Not connected, not zero vehicles.'
    ],
    cameraCount:cams.length, monitoredOnline:cams.filter(function(c){return c.status==='online' && c.last_seen &&
      (new Date().getTime()-new Date(c.last_seen).getTime())<150000;}).length
  };
}

/** Daily task creation — call via owner-installed trigger, or manually. */
function createOmCameraDailyChecks() {
  omOwner_();
  var day=omToday_(),existing={};
  omRead_('CameraChecks',5000).forEach(function(c){if(c.check_date===day)existing[c.store_id+'|'+c.camera_id]=true;});
  var newCount=0;
  omRead_('CameraConfig').forEach(function(c){
    if(existing[c.store_id+'|'+c.camera_id])return;
    omAppend_('CameraChecks',{id:omUid_('CHK'),store_id:c.store_id,camera_id:c.camera_id,check_date:day,
      task:c.task,assigned_to:c.observer,status:'Open',updated_at:omNow_(),notes:''});newCount++;
  });
  return {ok:true,created:newCount,date:day};
}
function installOmAiCameraDailyChecks() {
  omOwner_();
  ScriptApp.getProjectTriggers().filter(function(t){return t.getHandlerFunction()==='createOmCameraDailyChecks';}).forEach(ScriptApp.deleteTrigger);
  ScriptApp.newTrigger('createOmCameraDailyChecks').timeBased().everyDays(1).atHour(6).create();
  return 'Camera observer checks scheduled at approximately 6 AM script-timezone daily';
}
function setOmCameraCheckStatus(storeId,id,status) {
  var user=omAuth_();omStoreAccess_(user,storeId,true);
  if(['Open','In Progress','Reviewed','Needs Attention'].indexOf(status)<0)throw new Error('Invalid status');
  var found=omRead_('CameraChecks',5000).some(function(c){return c.id===id&&c.store_id===storeId;});
  if(!found)throw new Error('Camera check not found');
  return omLock_(function(){omPatch_('CameraChecks',id,{status:status,updated_at:omNow_()});
    omLog_('camera_check',storeId,id,status);return {ok:true};});
}
function assignOmCameraObserver(storeId,cameraId,observer) {
  var user=omAuth_();omStoreAccess_(user,storeId,true);
  if(user.role!=='Admin'&&user.role!=='Manager')throw new Error('Manager or Admin required');
  var existing=omRead_('CameraConfig').filter(function(c){return c.store_id===storeId&&c.camera_id===cameraId;})[0];
  if(!existing)throw new Error('Camera not found');
  return omLock_(function(){omPatch_('CameraConfig',cameraId,{observer:omClean_(observer,100)});
    omLog_('camera_assignment',storeId,cameraId,observer);return {ok:true};});
}

function omCameraIngest_(signed) {
  var secret=omProps_().getProperty('OM_CAMERA_SYNC_SECRET');
  if(!secret||secret.length<32)throw new Error('Camera ingestion not enabled');
  if(!signed||typeof signed.payload!=='string'||typeof signed.signature!=='string'||signed.payload.length>100000)
    throw new Error('Invalid signed payload');
  var bytes=Utilities.base64Decode(signed.payload),raw=Utilities.newBlob(bytes).getDataAsString('UTF-8');
  var sig=Utilities.computeHmacSha256Signature(raw,secret).map(function(b){return ('0'+(b&255).toString(16)).slice(-2);}).join('');
  var offered=String(signed.signature).toLowerCase();
  if(sig.length!==offered.length)throw new Error('Invalid signature');
  var delta=0;for(var si=0;si<sig.length;si++)delta|=sig.charCodeAt(si)^offered.charCodeAt(si);
  if(delta!==0)throw new Error('Invalid signature');
  var data=JSON.parse(raw);var now=Date.now(),time=Date.parse(data.sent_at);
  if(!isFinite(time)||Math.abs(now-time)>5*60*1000)throw new Error('Timestamp outside signed window');
  if(data.store_id!=='QUICKC')throw new Error('Store not configured for camera ingest');
  var hours=data.hours||[],cameras=data.cameras||[];
  if(!Array.isArray(hours)||hours.length>400||!Array.isArray(cameras)||cameras.length>25)throw new Error('Batch too large');
  var configs=omForStore_(omRead_('CameraConfig'),data.store_id),valid={};
  configs.forEach(function(c){valid[c.camera_id]=true;});
  var existing={};omForStore_(omRead_('CameraHour',15000),data.store_id).forEach(function(c){existing[c.id]=Number(c.count);});
  var added=0;
  omLock_(function(){
    hours.forEach(function(row){
      if(!valid[row.camera_id]&&row.camera_id!=='POS')throw new Error('Unknown camera');
      if(OM_CAMERA_METRICS_.indexOf(row.metric)<0)throw new Error('Unknown metric');
      if(!/^(camera_detection|pos_import|wash_controller|counter_monitor)$/.test(String(row.source)))throw new Error('Bad source');
      if(['fuel_transaction','carwash_paid'].indexOf(row.metric)>=0&&row.source!=='pos_import')throw new Error('POS evidence required');
      if(row.metric==='carwash_controller_cycle'&&row.source!=='wash_controller')throw new Error('Controller evidence required');
      var ts=String(row.hour_bucket);
      if(!/^\d{4}-\d{2}-\d{2}T\d{2}:00:00Z$/.test(ts)||!isFinite(Date.parse(ts))||
         Math.abs(Date.now()-Date.parse(ts))>3*86400*1000)throw new Error('Invalid hour');
      var count=Number(row.count);
      if(!Number.isSafeInteger(count)||count<0||count>50000)throw new Error('Invalid count');
      var id=[data.store_id,row.camera_id,ts,row.metric,row.source].join('|');
      var r={id:id,store_id:data.store_id,camera_id:row.camera_id,hour_bucket:ts,
        metric:row.metric,count:count,source:row.source,updated_at:omNow_()};
      if(Object.prototype.hasOwnProperty.call(existing,id)){
        if(existing[id]!==count){omPatch_('CameraHour',id,{count:count,updated_at:r.updated_at});existing[id]=count;}
      }else {omAppend_('CameraHour',r);existing[id]=count;added++;}
    });
    cameras.forEach(function(c){
      if(!valid[c.camera_id])return;
      var status=omEnum_(c.status,['online','offline','stale','not_connected'],'not_connected');
      var stamp=c.last_seen?String(c.last_seen):'';
      if(stamp&&!isFinite(Date.parse(stamp)))return;
      omPatch_('CameraConfig',c.camera_id,{status:status,last_seen:stamp});
    });
  });
  return {ok:true,accepted:hours.length,inserted:added,cameras:cameras.length};
}

/** Avoid conflicts with the authenticated UI's doGet(); this only accepts signed aggregates. */
function doPost(e) {
  var output;
  try {
    if(!e||!e.postData||!e.postData.contents||e.postData.contents.length>120000)throw new Error('Invalid request');
    var message=JSON.parse(e.postData.contents);
    output=message.kind==='wifi_snapshot'?omWifiIngest_(message):
      message.kind==='pc_task_snapshot'?omPcIngest_(message):omCameraIngest_(message);
  }catch(err){output={ok:false,error:String(err.message||err).slice(0,160)};}
  return ContentService.createTextOutput(JSON.stringify(output)).setMimeType(ContentService.MimeType.JSON);
}
