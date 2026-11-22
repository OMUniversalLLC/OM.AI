/** No API calls or real store data needed; built-in Node assertions. */
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import path from 'node:path';
const root=path.resolve(import.meta.dirname,'..');
const names=['Config','Setup','Analysis','Api','Monitor','AI','FuelSources','FuelImageImport','CameraSync','WifiMonitor'];
for(const file of names){
 const s=fs.readFileSync(path.join(root,'apps-script',file+'.gs'),'utf8');
 new vm.Script(s,{filename:file+'.gs'});
}
const client=fs.readFileSync(path.join(root,'apps-script','Client.html'),'utf8').replace(/^<script>\s*/,'').replace(/\s*<\/script>\s*$/,'');
new vm.Script(client,{filename:'Client.html'});
const ctx=vm.createContext({console,Date,Number,Math,JSON,isFinite,Utilities:{formatDate:(d,tz,fmt)=>new Date(d).toISOString().slice(0,10)}});
vm.runInContext(fs.readFileSync(path.join(root,'apps-script','Config.gs'),'utf8'),ctx);
vm.runInContext(fs.readFileSync(path.join(root,'apps-script','Analysis.gs'),'utf8'),ctx);
function date(shift){let d=new Date('2026-10-01T12:00:00Z');d.setUTCDate(d.getUTCDate()+shift);return d.toISOString().slice(0,10);}
const sales=Array.from({length:49},(_,i)=>({date:date(i),inside_sales:1000+(i%7)*100,customers:100,transactions:110,fuel_gallons:400,lottery_sales:250}));
let forecast=ctx.omForecast_(sales,date(49),7);
assert.equal(forecast.status,'baseline');
assert.equal(forecast.points.length,7);
assert.ok(forecast.points.every(x=>x.expected!==null && x.lower<=x.expected&&x.upper>=x.expected));
assert.equal(ctx.omForecast_([],date(49),7).status,'insufficient');
assert.equal(ctx.omClean_('=SUM(1,2)'),"'=SUM(1,2)");
assert.equal(ctx.omUrl_('javascript:alert(1)'),'');
assert.equal(ctx.omRound_(1030-20-990,2),20);
const summary=ctx.omSummary_(sales, [{invoice_total:1030,audit_total:990,discount:20,credit:0}], [{on_hand:2,reorder_point:6}], [{status:'Open',due_date:'2020-01-01'}],[],[],[],[]);
assert.equal(summary.low_stock_count,1);
assert.equal(summary.vendor_variance,20);
assert.equal(summary.latest_sales,1600);
const alerts=ctx.omAlerts_('QUICKC',sales,[],[{item_name:'Test item',on_hand:0,reorder_point:5}], [{title:'Overdue test',status:'Open',priority:'High',due_date:'2020-01-01'}],[],[],[],[]);
assert.ok(alerts.some(x=>x.title.includes('Low stock')));
assert.ok(alerts.some(x=>x.title.includes('Overdue')));
assert.equal(ctx.OM_SCHEMA.Stores.includes('longitude'),true);
assert.equal(ctx.OM_SCHEMA.Signals.includes('expires_at'),true);
assert.equal(ctx.OM_SCHEMA.Signals.includes('severity'),true);
assert.equal(ctx.OM_SCHEMA.CameraConfig.includes('camera_id'),true);
assert.equal(ctx.OM_SCHEMA.CameraHour.includes('hour_bucket'),true);
assert.equal(ctx.OM_SCHEMA.NetworkDevices.includes('device_id'),true);
assert.equal(ctx.OM_SCHEMA.NetworkStatus.includes('pc_wifi_receive_mbps'),true);
assert.equal(ctx.OM_SCHEMA.NetworkCameras.includes('status'),true);
console.log('PASS: JavaScript syntax, forecast baseline, missing-data state, alerts, invoice variance, URL/formula sanitization, tab schema.');
