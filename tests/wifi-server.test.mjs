import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const source=f=>fs.readFileSync(path.join(root,'apps-script',f+'.gs'),'utf8');
const secret='testing-wifi-secret-with-32-plus-chars-1234567';
const db={CameraConfig:[{camera_id:'CAM01',store_id:'QUICKC',name:'SIDE VIEW'}],NetworkStatus:[],NetworkDevices:[],NetworkCameras:[],NetworkEvents:[]};
const ctx=vm.createContext({Date,JSON,Number,Math,isFinite,console,Utilities:{
  base64Decode:s=>Array.from(Buffer.from(s,'base64')),newBlob:bytes=>({getDataAsString:()=>Buffer.from(bytes).toString('utf8')}),
  computeHmacSha256Signature:(s,key)=>Array.from(crypto.createHmac('sha256',key).update(s).digest()).map(x=>x>127?x-256:x)
}});
vm.runInContext(source('Config'),ctx);vm.runInContext(source('WifiMonitor'),ctx);
ctx.omProps_=()=>({getProperty:k=>k==='OM_WIFI_SYNC_SECRET'?secret:null});
ctx.omRead_=(name)=>db[name].map(x=>({...x}));
ctx.omForStore_=(rows,store)=>rows.filter(x=>x.store_id===store);
ctx.omLock_=fn=>fn();
ctx.omNow_=()=>new Date().toISOString();
ctx.omPatch_=(tab,id,data)=>{
  let first=ctx.OM_SCHEMA[tab][0];let target=db[tab].find(x=>x[first]===id);
  if(!target)throw Error('Missing row '+tab+' '+id);
  Object.assign(target,data);
};
ctx.omAppend_=(tab,data)=>db[tab].push({...data});
function sign(obj){let raw=JSON.stringify(obj),signature=crypto.createHmac('sha256',secret).update(raw).digest('hex');return {kind:'wifi_snapshot',payload:Buffer.from(raw).toString('base64'),signature};}
const report={kind:'wifi_snapshot',store_id:'QUICKC',sent_at:new Date().toISOString(),
  devices:[{device_id:'NVR',label:'iLink recorder',device_type:'nvr',connection:'wired_or_unknown',ip_address:'192.168.50.10',mac_masked:'',status:'reachable',method:'tcp_known_target',evidence:'TCP open',critical:true,latency_ms:14}],
  cameras:[{camera_id:'CAM01',name:'SIDE VIEW',status:'not_configured',method:'none',details:'not enabled'}],
  events:[],pc_wifi:{state:'not_available',ssid:'',signal_pct:null,receive_mbps:null,transmit_mbps:null},router_export_state:'not_configured'};
assert.equal(ctx.omWifiIngest_(sign(report)).ok,true);
assert.equal(db.NetworkDevices.length,1);
assert.equal(db.NetworkCameras.length,1);
assert.equal(ctx.omWifiPayload_('QUICKC').reachable_devices,1);
assert.equal(ctx.omWifiPayload_('QUICKC').verified_streams,0);
assert.equal(ctx.omWifiIngest_(sign(report)).new_devices,0);
let bad=sign(report);bad.signature='0'.repeat(64);
assert.throws(()=>ctx.omWifiIngest_(bad),/Invalid signature/);
assert.throws(()=>ctx.omWifiIngest_(sign({...report, cameras:[{camera_id:'CAM99',status:'stream_playable'}]})),/Unknown camera/);
assert.throws(()=>ctx.omWifiIngest_(sign({...report,sent_at:'2024-01-01T00:00:00Z'})),/timestamp/);
db.NetworkStatus[0].updated_at='2024-01-01T00:00:00Z';
assert.equal(ctx.omWifiPayload_('QUICKC').fresh,false);
assert.equal(ctx.omWifiPayload_('QUICKC').devices[0].status,'stale');
console.log('PASS: signed WiFi ingest, upsert idempotence, unknown-camera rejection, expiry, stale statuses, verified-stream separation');
