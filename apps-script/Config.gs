/** OM AI — shared configuration, Sheet IO and authorization. */
var OM_SCHEMA = {
  Users: ['email','name','role','store_ids','active'],
  Stores: ['store_id','name','address','latitude','longitude','timezone','active'],
  Sales: ['id','date','store_id','inside_sales','customers','transactions','fuel_gallons','fuel_sales','lottery_sales','car_wash_sales','notes','created_at'],
  Inventory: ['id','store_id','sku','item_name','department','on_hand','reorder_point','unit_cost','retail_price','updated_at'],
  Vendors: ['id','date','store_id','vendor','invoice_number','invoice_total','audit_total','discount','credit','status','notes','created_at'],
  Expenses: ['id','date','store_id','category','vendor','amount','payment_method','notes','created_at'],
  Operations: ['id','date','store_id','area','metric','value','unit','notes','created_at'],
  Compliance: ['id','store_id','name','category','due_date','owner','status','notes','created_at','updated_at'],
  Tasks: ['id','store_id','title','assigned_to','due_date','priority','status','notes','created_at','updated_at'],
  Incidents: ['id','date','store_id','category','severity','description','status','created_at'],
  ExternalEvents: ['id','store_id','event_date','category','title','description','severity','source_url','start_date','end_date','status','created_at'],
  Signals: ['id','store_id','source','kind','observed_at','title','value','unit','details','source_url','source_key','expires_at','severity'],
  FuelSources: ['source_id','name','url','purpose','data_kind','capture_mode','schedule','active','notes'],
  FuelObservations: ['id','store_id','price_date','source_id','grade','area_station','price_type','price_gallon','reported_at','source_url','evidence_url','verified_by','notes','created_at'],
  FuelReports: ['id','store_id','report_date','grade','opening_gallons','delivered_gallons','sold_gallons','closing_gallons_actual','cash_price','card_price','replacement_cost','source_report_id','evidence_url','verified_by','notes','created_at'],
  FuelSourceTasks: ['id','store_id','source_id','task_date','task','status','assigned_to','due_date','completed_at','evidence_url','notes','created_at'],
  CameraConfig: ['camera_id','store_id','name','role','observer','task','status','last_seen','secure_view_url','notes'],
  CameraHour: ['id','store_id','camera_id','hour_bucket','metric','count','source','updated_at'],
  CameraChecks: ['id','store_id','camera_id','check_date','task','assigned_to','status','updated_at','notes'],
  NetworkStatus: ['store_id','updated_at','pc_wifi_state','pc_wifi_ssid','pc_wifi_signal','pc_wifi_receive_mbps','pc_wifi_transmit_mbps','router_export_state','seen_devices','network_note'],
  NetworkDevices: ['device_id','store_id','label','device_type','connection','ip_address','mac_masked','status','method','last_checked','latency_ms','evidence','critical'],
  NetworkCameras: ['id','store_id','camera_id','name','status','checked_at','method','details'],
  NetworkEvents: ['id','store_id','device_id','occurred_at','kind','severity','details','source'],
  PcStatus: ['device_id','store_id','updated_at','status','cpu_pct','ram_pct','ram_used_gb','ram_available_gb','disk_pct','disk_free_gb','gpu_pct','cpu_temp_c','gpu_temp_c','uptime_hours','sensor_source','process_note','processes_json','critical_json','safety_note'],
  PcJobs: ['id','store_id','job_id','name','provider','owner','state','last_run','age_hours','max_age_hours','detail','next_action','evidence_ref','checked_at'],
  ServiceJobs: ['id','store_id','job_id','name','provider','owner','state','last_run','age_hours','max_age_hours','detail','next_action','evidence_ref','checked_at'],
  PcAlerts: ['id','store_id','device_id','observed_at','kind','severity','title','detail','next_action','approval_required','source'],
  JobReviews: ['id','store_id','job_id','decision','reviewed_by','reviewed_at','notes'],
  AuditLog: ['id','occurred_at','actor','action','store_id','record_id','details']
};
var OM_PRIMARY_STORE = 'QUICKC';
var OM_ALLOWED_ROLES = ['Admin','Manager','Viewer'];

function omProps_() { return PropertiesService.getScriptProperties(); }
function omNow_() { return new Date().toISOString(); }
function omToday_() { return Utilities.formatDate(new Date(), 'America/New_York', 'yyyy-MM-dd'); }
function omUid_(prefix) { return prefix + '-' + Utilities.getUuid().slice(0, 12); }
function omClean_(value, max) {
  var s = String(value == null ? '' : value).trim().slice(0, max || 1000);
  // A text cell must never become a formula supplied by a user/API/news feed.
  return /^[=+@-]/.test(s) ? "'" + s : s;
}
function omNum_(v, def) {
  var n = Number(v);
  return isFinite(n) ? n : (def == null ? 0 : def);
}
function omDate_(date) {
  var s = String(date || '').trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s) || isNaN(Date.parse(s + 'T12:00:00Z'))) throw new Error('Enter a valid date (YYYY-MM-DD).');
  return s;
}
function omUrl_(v) {
  var s = String(v || '').trim().slice(0, 1000);
  return /^https:\/\/[a-z0-9.-]+(?:[/:?#]|$)/i.test(s) ? s : '';
}
function omEnum_(v, allowed, fallback) { return allowed.indexOf(String(v)) >= 0 ? String(v) : fallback; }
function omDb_() {
  var id = omProps_().getProperty('OM_AI_SHEET_ID');
  if (!id) throw new Error('OM AI not configured: run setupOmAi() as the owner.');
  return SpreadsheetApp.openById(id);
}
function omRead_(name, limit) {
  var sh = omDb_().getSheetByName(name);
  if (!sh) throw new Error('Missing worksheet: ' + name);
  var last = sh.getLastRow();
  if (last < 2) return [];
  var first = limit ? Math.max(2, last - limit + 1) : 2;
  var data = sh.getRange(first, 1, last - first + 1, OM_SCHEMA[name].length).getValues();
  return data.map(function(a) {
    var out = {};
    OM_SCHEMA[name].forEach(function(h,i) {
      var v=a[i];
      out[h] = v instanceof Date ? Utilities.formatDate(v, 'Etc/UTC', "yyyy-MM-dd'T'HH:mm:ss'Z'") : v;
    });
    return out;
  }).filter(function(row) { return row[OM_SCHEMA[name][0]] !== ''; });
}
function omAppend_(name, row) {
  var sh = omDb_().getSheetByName(name);
  if (!sh) throw new Error('Missing worksheet: '+name);
  sh.appendRow(OM_SCHEMA[name].map(function(h) { return row[h] == null ? '' : row[h]; }));
  return row;
}
function omPatch_(name, id, updates) {
  var sh = omDb_().getSheetByName(name), keys = OM_SCHEMA[name];
  var last = sh.getLastRow();
  if (last < 2) throw new Error('Record not found.');
  var ids = sh.getRange(2,1,last-1,1).getValues();
  for (var i=0;i<ids.length;i++) {
    if (String(ids[i][0]) === String(id)) {
      keys.forEach(function(k, ci) {
        if (Object.prototype.hasOwnProperty.call(updates,k)) sh.getRange(i+2,ci+1).setValue(updates[k]);
      });
      return true;
    }
  }
  throw new Error('Record not found.');
}
function omActor_() {
  var email = String(Session.getActiveUser().getEmail() || '').toLowerCase().trim();
  if (!email) throw new Error('Your Google email is unavailable. Deploy as USER_ACCESSING and sign in with an authorized account.');
  return email;
}
function omAuth_() {
  var email=omActor_();
  var user = omRead_('Users').filter(function(x){return String(x.email).toLowerCase() === email && String(x.active).toLowerCase() === 'yes';})[0];
  if (!user) throw new Error('Access denied: this email is not active in the OM AI Users sheet.');
  user.role = omEnum_(user.role, OM_ALLOWED_ROLES,'Viewer');
  user.storeList = String(user.store_ids || '').split(',').map(function(x){return x.trim();}).filter(Boolean);
  return user;
}
function omStoreAccess_(user, storeId, write) {
  if (write && user.role === 'Viewer') throw new Error('Viewer accounts are read-only.');
  var available = omRead_('Stores').filter(function(s){return String(s.active).toLowerCase() === 'yes';});
  var store=available.filter(function(x){return x.store_id === storeId;})[0];
  if (!store) throw new Error('Unknown or disabled store.');
  if (user.role !== 'Admin' && user.storeList.indexOf(storeId) < 0) throw new Error('Your account is not authorized for this store.');
  return store;
}
function omOwner_() {
  var expected = omProps_().getProperty('OWNER_EMAIL');
  if (!expected) throw new Error('First configure OWNER_EMAIL in Script Properties.');
  var actual=String(Session.getActiveUser().getEmail()||Session.getEffectiveUser().getEmail()||'').toLowerCase().trim();
  if (actual !== expected.toLowerCase().trim()) throw new Error('Owner permission required.');
}
function omLog_(action,storeId,recordId,detail) {
  omAppend_('AuditLog',{id:omUid_('LOG'),occurred_at:omNow_(),actor:omActor_(),action:action,store_id:storeId||'',record_id:recordId||'',details:omClean_(detail,450)});
}
function omLock_(fn) {
  var lock=LockService.getScriptLock();
  if (!lock.tryLock(10000)) throw new Error('OM AI is busy. Try your action again.');
  try { return fn(); } finally { lock.releaseLock(); }
}
function omJson_(url, headers) {
  var res=UrlFetchApp.fetch(url,{muteHttpExceptions:true,followRedirects:true,headers:headers||{'Accept':'application/json'},timeout:20000});
  var status=res.getResponseCode();
  if (status < 200 || status>=300) throw new Error('Source HTTP '+status+' for '+url.split('?')[0]);
  return JSON.parse(res.getContentText());
}
