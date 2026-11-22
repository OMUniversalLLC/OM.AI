/**
 * OM AI Fuel Sources — three independent source queues and a normalized daily fuel report.
 * Deliberately DOES NOT scrape GasBuddy, AAA or private MostEdge accounts.
 * Input options: manually checked observations, permitted provider exports, or an approved API.
 * Every observation must retain provenance (date, station/geography, source URL, evidence).
 */
function omSeedFuelSources_() {
  var old=omRead_('FuelSources');
  if(old.length)return;
  [
    {source_id:'GasBuddy',name:'GasBuddy nearby prices',url:'https://www.gasbuddy.com/home',purpose:'Verify competitor stations within selected radius, price types and reported timestamps',data_kind:'station-reported',capture_mode:'Manual verified entry / licensed data',schedule:'Daily',active:'Yes',notes:'Crowdsourced prices may be stale; never assume live.'},
    {source_id:'AAA',name:'AAA fuel market averages',url:'https://gasprices.aaa.com/?state=FL',purpose:'Record Florida and Hillsborough average by fuel grade',data_kind:'market-average',capture_mode:'Manual verified entry / approved feed',schedule:'Daily',active:'Yes',notes:'An average is not a nearby station price.'},
    {source_id:'MostEdge',name:'MostEdge store fuel report',url:'https://www.mostedge.com/',purpose:'Record owned store costs, deliveries, tank variance, price and margins',data_kind:'private-store-report',capture_mode:'Authorized export / manual verified entry',schedule:'Daily',active:'Yes',notes:'Requires own authorized report; do not scrape account or publish sensitive data.'}
  ].forEach(function(x){omAppend_('FuelSources',x);});
}
function omFuelNumber_(value,field) {
  var n=Number(value);
  if(value==null||String(value).trim()===''||!isFinite(n)||n<0||n>10000000)throw new Error('Enter valid '+field+'.');
  return n;
}
function omFuelOptional_(value,field){return (value==null||String(value).trim()==='')?'':omFuelNumber_(value,field);}
function omFuelGrade_(value){return omEnum_(value,['Regular','Midgrade','Premium','Diesel'],'Regular');}
function omFuelPayload_(storeId){
  var sources=omRead_('FuelSources');
  var observations=omForStore_(omRead_('FuelObservations',1200),storeId).sort(function(a,b){return String(b.price_date+' '+b.reported_at).localeCompare(String(a.price_date+' '+a.reported_at));});
  var reports=omForStore_(omRead_('FuelReports',1200),storeId).sort(function(a,b){return String(b.report_date).localeCompare(String(a.report_date));});
  var tasks=omForStore_(omRead_('FuelSourceTasks',800),storeId).sort(function(a,b){return String(b.task_date).localeCompare(String(a.task_date));});
  var latest={};sources.forEach(function(s){
    var matches=observations.filter(function(x){return x.source_id===s.source_id;});
    latest[s.source_id]={last_seen:matches.length?matches[0].reported_at||matches[0].price_date:'',count:matches.length};
  });
  latest.MostEdge={last_seen:reports.length?reports[0].report_date:'',count:reports.length};
  var enriched=reports.slice(0,50).map(function(r){
    var calc=Number(r.opening_gallons)+Number(r.delivered_gallons)-Number(r.sold_gallons);
    var actual=Number(r.closing_gallons_actual),cash=Number(r.cash_price),card=Number(r.card_price),cost=Number(r.replacement_cost);
    var hasCost=r.replacement_cost!==''&&r.replacement_cost!=null;
    var grade=String(r.grade),day=String(r.report_date);
    var matches=observations.filter(function(x){return x.price_date===day&&x.grade===grade;});
    var aaa=matches.filter(function(x){return x.source_id==='AAA'&&x.price_type==='Average';});
    var gb=matches.filter(function(x){return x.source_id==='GasBuddy'&&String(x.price_type).toLowerCase()==='cash';});
    var aaaval=aaa.length?Number(aaa[0].price_gallon):null;
    var gbval=gb.length?Math.min.apply(null,gb.map(function(x){return Number(x.price_gallon);})):null;
    return {id:r.id,report_date:day,grade:grade,opening_gallons:r.opening_gallons,delivered_gallons:r.delivered_gallons,sold_gallons:r.sold_gallons,
      expected_closing:Math.round(calc*100)/100,actual_closing:r.closing_gallons_actual,variance:Math.round((actual-calc)*100)/100,
      cash_price:r.cash_price,card_price:r.card_price,replacement_cost:r.replacement_cost,
      cash_margin:hasCost?Math.round((cash-cost)*1000)/1000:null,card_margin:hasCost?Math.round((card-cost)*1000)/1000:null,
      aaa_average:aaaval,gasbuddy_low_cash:gbval,
      cash_vs_aaa:aaaval==null?null:Math.round((cash-aaaval)*1000)/1000,
      cash_vs_gasbuddy:gbval==null?null:Math.round((cash-gbval)*1000)/1000,
      evidence_url:r.evidence_url,source_report_id:r.source_report_id,verified_by:r.verified_by};
  });
  return {sources:sources,latest:latest,observations:observations.slice(0,100),reports:enriched,tasks:tasks.slice(0,100),
    freshness_note:'Values entered from cited sources; no public price scraping; missing observations are unavailable, not $0.'};
}
function getOmAiFuelSources(storeId){var user=omAuth_();omStoreAccess_(user,storeId,false);return omFuelPayload_(storeId);}
function saveOmAiFuelObservation(storeId,data){
  var user=omAuth_();omStoreAccess_(user,storeId,true);data=data||{};
  var source=omEnum_(data.source_id,['GasBuddy','AAA'],'');
  if(!source)throw new Error('Choose GasBuddy or AAA; MostEdge report values belong in Fuel Reports.');
  var priceType=omEnum_(data.price_type,['Cash','Card','Average','Unknown'],'Unknown');
  if(source==='AAA'&&priceType!=='Average')throw new Error('AAA should be captured as an average, not a station cash price.');
  if(source==='GasBuddy'&&priceType==='Average')throw new Error('GasBuddy competitor prices should specify Cash, Card or Unknown (not area Average).');
  var area=omClean_(data.area_station,130);if(!area)throw new Error('Station or area is required.');
  var url=omUrl_(data.source_url),evidence=omUrl_(data.evidence_url);
  if(!url)throw new Error('The original HTTPS source URL is required for auditability.');
  var row={id:omUid_('FPO'),store_id:storeId,price_date:omDate_(data.price_date),source_id:source,grade:omFuelGrade_(data.grade),
    area_station:area,price_type:priceType,price_gallon:omFuelNumber_(data.price_gallon,'price per gallon'),
    reported_at:omClean_(data.reported_at,45),source_url:url,evidence_url:evidence,
    verified_by:user.email,notes:omClean_(data.notes,400),created_at:omNow_()};
  return omLock_(function(){omAppend_('FuelObservations',row);omLog_('fuel_price_observation',storeId,row.id,source+' '+row.grade);return {ok:true,id:row.id};});
}
function saveOmAiFuelReport(storeId,data){
  var user=omAuth_();omStoreAccess_(user,storeId,true);data=data||{};
  var row={id:omUid_('FUR'),store_id:storeId,report_date:omDate_(data.report_date),grade:omFuelGrade_(data.grade),
    opening_gallons:omFuelNumber_(data.opening_gallons,'opening gallons'),delivered_gallons:omFuelNumber_(data.delivered_gallons,'delivered gallons'),
    sold_gallons:omFuelNumber_(data.sold_gallons,'sold gallons'),closing_gallons_actual:omFuelNumber_(data.closing_gallons_actual,'closing gallons'),
    cash_price:omFuelNumber_(data.cash_price,'cash price'),card_price:omFuelNumber_(data.card_price,'card price'),
    replacement_cost:omFuelOptional_(data.replacement_cost,'replacement cost'),source_report_id:omClean_(data.source_report_id,70),
    evidence_url:omUrl_(data.evidence_url),verified_by:user.email,notes:omClean_(data.notes,400),created_at:omNow_()};
  if(omRead_('FuelReports').some(function(x){return x.store_id===storeId&&x.report_date===row.report_date&&x.grade===row.grade;}))
    throw new Error('Report exists for this store, date and grade. Review or correct it in the private Sheet; do not duplicate.');
  return omLock_(function(){omAppend_('FuelReports',row);omLog_('fuel_daily_report',storeId,row.id,row.report_date+' '+row.grade);return {ok:true,id:row.id};});
}
/** Owner-installed daily checklist; no provider robots and no implied automated site access. */
function scheduledOmAiFuelTasks(){
  omOwner_();var now=omToday_(),sources=omRead_('FuelSources').filter(function(x){return x.active==='Yes';});
  var stores=omRead_('Stores').filter(function(x){return x.active==='Yes';});
  return omLock_(function(){var prior={};omRead_('FuelSourceTasks',2000).forEach(function(r){prior[r.store_id+'|'+r.task_date+'|'+r.source_id]=true;});
    var count=0;stores.forEach(function(s){sources.forEach(function(src){var key=s.store_id+'|'+now+'|'+src.source_id;if(prior[key])return;
      var label=src.source_id==='GasBuddy'?'Verify nearby competitor prices and timestamps':src.source_id==='AAA'?'Capture FL and county averages by grade':'Import approved daily fuel report and reconcile tank gallons, costs and sales';
      omAppend_('FuelSourceTasks',{id:omUid_('FST'),store_id:s.store_id,source_id:src.source_id,task_date:now,task:label,status:'Pending',assigned_to:'Fuel manager',due_date:now,
        completed_at:'',evidence_url:'',notes:src.notes,created_at:omNow_()});count++;prior[key]=true;
    });});return {created:count,date:now};});
}
function installOmAiFuelDailyTasks(){
  omOwner_();ScriptApp.getProjectTriggers().filter(function(t){return t.getHandlerFunction()==='scheduledOmAiFuelTasks';}).forEach(ScriptApp.deleteTrigger);
  ScriptApp.newTrigger('scheduledOmAiFuelTasks').timeBased().atHour(7).nearMinute(0).everyDays(1).inTimezone('America/New_York').create();
  return 'Daily task check installed, around 7:00 AM Eastern. This creates review tasks; it does NOT scrape these websites.';
}
function setOmAiFuelTaskStatus(storeId,taskId,status,evidenceUrl){
  var user=omAuth_();omStoreAccess_(user,storeId,true);status=omEnum_(status,['Pending','Working','Needs Review','Completed','Blocked'],'');
  if(!status)throw new Error('Invalid status.');
  var task=omRead_('FuelSourceTasks').filter(function(x){return x.store_id===storeId&&x.id===taskId;})[0];if(!task)throw new Error('Fuel task not found.');
  if(status==='Completed'&&!omUrl_(evidenceUrl||task.evidence_url))throw new Error('A source report or screenshot evidence URL is required to complete this task.');
  return omLock_(function(){omPatch_('FuelSourceTasks',taskId,{status:status,completed_at:status==='Completed'?omNow_():'',evidence_url:omUrl_(evidenceUrl||task.evidence_url)});
    omLog_('fuel_source_task',storeId,taskId,status);return {ok:true};});
}
