/** OM WiFi Intelligence — signed, status-only ingestion for privately monitored LAN.
 * DO NOT send router passwords, camera credentials, raw surveillance footage or unmasked MACs.
 * Script Properties: OM_WIFI_SYNC_SECRET (random >=32 chars).
 * The public existing GitHub site must NEVER host this endpoint or its responses.
 */
var OM_WIFI_DEV_STATES_=['reachable','no_response','suspected_offline','not_configured',
  'observed_in_cache','router_reported_connected','router_export_unverified'];
var OM_WIFI_CAMERA_STATES_=['not_configured','stream_playable','probe_failed'];
function omWifiSafeId_(id) {
  id=String(id||'').trim();
  if(!/^[A-Z0-9_\-]{1,30}$/.test(id))throw new Error('Invalid network device ID');
  return id;
}
function omWifiIngest_(envelope) {
  var secret=omProps_().getProperty('OM_WIFI_SYNC_SECRET');
  if(!secret||secret.length<32)throw new Error('WiFi ingestion not configured');
  if(!envelope||envelope.kind!=='wifi_snapshot'||typeof envelope.payload!=='string'||
     typeof envelope.signature!=='string'||envelope.payload.length>110000)throw new Error('Malformed network packet');
  var raw=Utilities.newBlob(Utilities.base64Decode(envelope.payload)).getDataAsString('UTF-8');
  var expected=Utilities.computeHmacSha256Signature(raw,secret).map(function(b){return ('0'+(b&255).toString(16)).slice(-2);}).join('');
  var offered=String(envelope.signature).toLowerCase(),difference=0;
  if(expected.length!==offered.length)throw new Error('Invalid signature');
  for(var h=0;h<expected.length;h++)difference|=expected.charCodeAt(h)^offered.charCodeAt(h);
  if(difference!==0)throw new Error('Invalid signature');
  var data=JSON.parse(raw);
  if(data.kind!=='wifi_snapshot'||data.store_id!=='QUICKC')throw new Error('Unsupported network packet');
  if(!isFinite(Date.parse(data.sent_at))||Math.abs(Date.now()-Date.parse(data.sent_at))>300000)
    throw new Error('Network timestamp outside allowed window');
  if(!Array.isArray(data.devices)||data.devices.length>100||
     !Array.isArray(data.cameras)||data.cameras.length>32||
     !Array.isArray(data.events)||data.events.length>30)throw new Error('Network batch too large');
  var knownCameras={};omForStore_(omRead_('CameraConfig',100),data.store_id).forEach(function(c){knownCameras[c.camera_id]=true;});
  var eventsExisting={};omForStore_(omRead_('NetworkEvents',1500),data.store_id).forEach(function(x){eventsExisting[x.id]=true;});
  // Validate all rows BEFORE mutating the Sheets to avoid mixed partial state.
  var devices=data.devices.map(function(x){
    var id=omWifiSafeId_(x.device_id),status=omEnum_(x.status,OM_WIFI_DEV_STATES_,'not_configured');
    return {device_id:id,store_id:data.store_id,label:omClean_(x.label,80),device_type:omClean_(x.device_type,28),
      connection:omEnum_(x.connection,['wired','wifi','unknown','wired_or_unknown','wired_or_wifi'],'unknown'),
      ip_address:omClean_(x.ip_address,48),mac_masked:omClean_(x.mac_masked,24),status:status,
      method:omEnum_(x.method,['tcp_known_target','neighbor_cache','router_export'],'neighbor_cache'),
      last_checked:String(data.sent_at),latency_ms:(x.latency_ms==null?'':Math.max(0,Math.min(50000,Number(x.latency_ms)||0))),
      evidence:omClean_(x.evidence,170),critical:x.critical===true?'Yes':'No'};
  });
  var cameras=data.cameras.map(function(x){
    if(!knownCameras[x.camera_id])throw new Error('Unknown camera stream');
    return {id:data.store_id+'|'+x.camera_id,store_id:data.store_id,camera_id:x.camera_id,
      name:omClean_(x.name,70),status:omEnum_(x.status,OM_WIFI_CAMERA_STATES_,'not_configured'),
      checked_at:String(data.sent_at),method:omEnum_(x.method,['none','ffprobe'],'none'),
      details:omClean_(x.details,180)};
  });
  var wifi=data.pc_wifi||{};
  var network={store_id:data.store_id,updated_at:String(data.sent_at),
    pc_wifi_state:omEnum_(wifi.state,['connected','disconnected','unknown','not_available'],'unknown'),
    pc_wifi_ssid:omClean_(wifi.ssid,70),pc_wifi_signal:(wifi.signal_pct==null?'':Math.max(0,Math.min(100,Number(wifi.signal_pct)||0))),
    pc_wifi_receive_mbps:(wifi.receive_mbps==null?'':Math.max(0,Math.min(100000,Number(wifi.receive_mbps)||0))),
    pc_wifi_transmit_mbps:(wifi.transmit_mbps==null?'':Math.max(0,Math.min(100000,Number(wifi.transmit_mbps)||0))),
    router_export_state:omEnum_(data.router_export_state,['not_configured','missing_export','unreadable_export','stale','recent_export'],'not_configured'),
    seen_devices:devices.length,network_note:'Device results are connection checks, router exports or cache observations; no automatic unauthorized-device claim.'};
  var history=data.events.map(function(x){
    var id=omWifiSafeId_(x.device_id),stamp=String(x.occurred_at||'');
    if(!isFinite(Date.parse(stamp))||Math.abs(Date.now()-Date.parse(stamp))>86400000)throw new Error('Bad event time');
    var key=data.store_id+'|'+id+'|'+String(x.kind||'').slice(0,24)+'|'+stamp;
    return {id:key,store_id:data.store_id,device_id:id,occurred_at:stamp,
      kind:omEnum_(x.kind,['status_changed'],'status_changed'),severity:omEnum_(x.severity,['high','info'],'info'),
      details:omClean_(x.details,200),source:'local_network_agent'};
  });
  var deviceExisting={};omForStore_(omRead_('NetworkDevices',250),data.store_id).forEach(function(x){deviceExisting[x.device_id]=true;});
  var camExisting={};omForStore_(omRead_('NetworkCameras',70),data.store_id).forEach(function(x){camExisting[x.id]=true;});
  var networkExists=omRead_('NetworkStatus').some(function(x){return x.store_id===data.store_id;});
  var added=0;
  omLock_(function(){
    if(networkExists)omPatch_('NetworkStatus',data.store_id,network);else omAppend_('NetworkStatus',network);
    devices.forEach(function(d){if(deviceExisting[d.device_id])omPatch_('NetworkDevices',d.device_id,d);
      else{omAppend_('NetworkDevices',d);added++;}});
    cameras.forEach(function(c){if(camExisting[c.id])omPatch_('NetworkCameras',c.id,c);else omAppend_('NetworkCameras',c);});
    history.forEach(function(e){if(!eventsExisting[e.id]){omAppend_('NetworkEvents',e);eventsExisting[e.id]=true;}});
  });
  return {ok:true,store_id:data.store_id,devices:devices.length,cameras:cameras.length,new_devices:added,events:history.length};
}

function omWifiPayload_(storeId){
  var snap=omRead_('NetworkStatus').filter(function(x){return x.store_id===storeId;})[0]||{};
  var items=omForStore_(omRead_('NetworkDevices',400),storeId);
  var cams=omForStore_(omRead_('NetworkCameras',90),storeId);
  var history=omForStore_(omRead_('NetworkEvents',900),storeId).sort(function(a,b){return String(b.occurred_at).localeCompare(String(a.occurred_at));}).slice(0,40);
  var old=!snap.updated_at||!isFinite(Date.parse(snap.updated_at))||(Date.now()-Date.parse(snap.updated_at)>900000);
  function current(s){return old?'stale':s;}
  var devices=items.map(function(x){return Object.assign({},x,{status:current(x.status)});});
  var cameras=cams.map(function(x){return Object.assign({},x,{status:current(x.status)});});
  return {configured:!!snap.updated_at,fresh:!old,last_checked:snap.updated_at||'',
    pc_wifi_state:old?'unknown':(snap.pc_wifi_state||'unknown'),
    pc_wifi_ssid:old?'':(snap.pc_wifi_ssid||''),pc_wifi_signal:old?'':snap.pc_wifi_signal,
    pc_wifi_receive_mbps:old?'':snap.pc_wifi_receive_mbps,pc_wifi_transmit_mbps:old?'':snap.pc_wifi_transmit_mbps,
    router_export_state:snap.router_export_state||'not_configured',
    devices:devices,cameras:cameras,events:history,
    total_devices:devices.length,reachable_devices:devices.filter(function(x){return x.status==='reachable';}).length,
    suspected_offline:devices.filter(function(x){return x.status==='suspected_offline';}).length,
    verified_streams:cameras.filter(function(x){return x.status==='stream_playable';}).length,
    monitored_streams:cameras.filter(function(x){return x.status!=='not_configured'&&x.status!=='stale';}).length,
    note:'Router association, TCP reachability and camera stream checks measure different things. Unrecognized does not mean unauthorized.'};
}
