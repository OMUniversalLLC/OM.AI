/** Deterministic KPI, alerts and forecast calculations; NO invented live values. */
function omForStore_(rows,storeId) { return rows.filter(function(x){return x.store_id===storeId;}); }
function omDateSerial_(date) { return Date.parse(String(date).slice(0,10)+'T12:00:00Z'); }
function omRound_(n,d) { var p=Math.pow(10,d||0); return Math.round((n+Number.EPSILON)*p)/p; }
function omSummary_(sales,vendors,inventory,tasks,events,incidents,expenses,compliance) {
  expenses=expenses||[]; compliance=compliance||[];
  var sorted=sales.slice().sort(function(a,b){return String(a.date).localeCompare(String(b.date));});
  var latest=sorted[sorted.length-1]||null;
  var last7=sorted.slice(-7), prev7=sorted.slice(-14,-7);
  var sum=function(a,key){return a.reduce(function(s,x){return s+omNum_(x[key]);},0);};
  var mean=function(a,key){return a.length?sum(a,key)/a.length:null;};
  var low=inventory.filter(function(x){return omNum_(x.on_hand)<=omNum_(x.reorder_point);});
  var overdue=tasks.filter(function(x){return x.due_date && x.due_date<omToday_() && x.status!=='Completed' && x.status!=='Cancelled';});
  var vendorVariance=vendors.filter(function(v){return v.status!=='Resolved';}).reduce(function(t,v){return t+Math.abs(omNum_(v.audit_total)-(omNum_(v.invoice_total)-omNum_(v.discount)-omNum_(v.credit)));},0);
  var dateSeries=sorted.slice(-45).map(function(x){return {date:x.date,sales:omNum_(x.inside_sales),customers:omNum_(x.customers),fuel:omNum_(x.fuel_sales)};});
  var trend=mean(prev7,'inside_sales') && mean(last7,'inside_sales')!==null ? (mean(last7,'inside_sales')-mean(prev7,'inside_sales'))/mean(prev7,'inside_sales')*100 : null;
  return {latest_date:latest?latest.date:null,latest_sales:latest?omNum_(latest.inside_sales):null,latest_customers:latest?omNum_(latest.customers):null,
    latest_avg_ticket:latest&&omNum_(latest.transactions)>0?omRound_(omNum_(latest.inside_sales)/omNum_(latest.transactions),2):null,
    sales_last7:sum(last7,'inside_sales'),sales_prev7:sum(prev7,'inside_sales'),change_pct:trend===null?null:omRound_(trend,1),sales_days:sales.length,
    fuel_gallons_last7:sum(last7,'fuel_gallons'),lottery_last7:sum(last7,'lottery_sales'),low_stock_count:low.length,open_tasks:tasks.filter(function(x){return x.status!=='Completed'&&x.status!=='Cancelled';}).length,
    overdue_tasks:overdue.length,open_incidents:incidents.filter(function(x){return x.status!=='Resolved';}).length,
    vendor_variance:omRound_(vendorVariance,2),expenses_last7:omRound_(sum(expenses.filter(function(x){return x.date>=new Date(Date.now()-7*86400000).toISOString().slice(0,10);}), 'amount'),2),compliance_due:compliance.filter(function(x){return x.status!=='Completed' && x.due_date && x.due_date<=new Date(Date.now()+30*86400000).toISOString().slice(0,10);}).length,upcoming_events:events.filter(function(x){return x.start_date >= omToday_() && x.status !== 'Closed';}).length,
    series:dateSeries};
}
function omAlerts_(storeId,sales,vendors,inventory,tasks,incidents,events,signals,compliance) {
  compliance=compliance||[];
  var alerts=[], today=omToday_();
  function add(severity,title,details,source,url){alerts.push({severity:severity,title:title,details:details,source:source,url:url||'',store_id:storeId});}
  tasks.filter(function(t){return t.due_date && t.due_date<today && t.status!=='Completed'&&t.status!=='Cancelled';}).slice(0,8).forEach(function(t){add(t.priority==='High'?'high':'medium','Overdue: '+t.title,'Due '+t.due_date+' · Owner '+(t.assigned_to||'unassigned'),'Tasks','');});
  inventory.filter(function(i){return omNum_(i.on_hand)<=omNum_(i.reorder_point);}).slice(0,12).forEach(function(i){add(omNum_(i.on_hand)<=0?'high':'medium','Low stock: '+i.item_name,omNum_(i.on_hand)+' left · Reorder at '+omNum_(i.reorder_point),'Inventory','');});
  vendors.filter(function(v){return Math.abs(omNum_(v.audit_total)-(omNum_(v.invoice_total)-omNum_(v.discount)-omNum_(v.credit)))>0.01 && v.status!=='Resolved';}).slice(-10).forEach(function(v){
    var diff=omRound_(omNum_(v.audit_total)-(omNum_(v.invoice_total)-omNum_(v.discount)-omNum_(v.credit)),2);
    add(Math.abs(diff)>=50?'high':'medium','Vendor variance: '+v.vendor,'Invoice '+v.invoice_number+' · Audit minus net invoice: $'+diff.toFixed(2),'Vendor audit','');
  });
  incidents.filter(function(i){return i.status!=='Resolved' && i.severity==='High';}).slice(-5).forEach(function(i){add('high','Open incident: '+i.category,i.description,'Incident','');});
  events.filter(function(e){return e.status==='Active' || (e.start_date <= today && e.end_date >= today);}).slice(-8).forEach(function(e){add(String(e.severity).toLowerCase()==='high'?'high':'info',e.title,e.description,'External event',e.source_url);});
  compliance.filter(function(c){return c.status!=='Completed' && c.due_date && c.due_date<=new Date(Date.now()+30*86400000).toISOString().slice(0,10);}).slice(0,8).forEach(function(c){add(c.due_date<today?'high':'medium','Compliance due: '+c.name,'Due '+c.due_date+' · Owner '+(c.owner||'unassigned'),'Compliance','');});
  var lastSale=sales.slice().sort(function(a,b){return String(b.date).localeCompare(String(a.date));})[0];
  if (!lastSale) add('info','No sales data connected','Add daily sales or import historical data to enable forecasts.','Data quality','');
  else if ((omDateSerial_(today)-omDateSerial_(lastSale.date))/86400000>2) add('medium','Daily sales appear stale','Latest sales record: '+lastSale.date,'Data quality','');
  signals.filter(function(s){return s.kind==='weather_alert' && (!s.expires_at || Date.parse(s.expires_at)>Date.now()) && omDateSerial_(s.observed_at.slice(0,10))>=omDateSerial_(today)-86400000;}).slice(-4).forEach(function(s){add(['Extreme','Severe'].indexOf(s.severity)>=0?'high':s.severity==='Minor'?'info':'medium',s.title,s.details,'NWS',s.source_url);});
  signals.filter(function(s){return s.kind==='traffic_incident' && Date.now()-Date.parse(s.observed_at)<2*3600000;}).slice(-4).forEach(function(s){add('medium','Recent traffic report: '+s.title,s.details+' · Verify current status with live traffic maps.','TomTom',s.source_url);});
  var rank={high:0,medium:1,info:2};
  return alerts.sort(function(a,b){return rank[a.severity]-rank[b.severity];}).slice(0,40);
}
function omForecast_(sales,startDate,count) {
  var valid=sales.filter(function(x){return x.date && omNum_(x.inside_sales)>=0;}).sort(function(a,b){return a.date.localeCompare(b.date);});
  if (valid.length<14) return {status:'insufficient',method:'Same-weekday baseline',required:14,available:valid.length,points:[],note:'At least 14 dated sales records are required. 6–8 weeks is recommended.'};
  var results=[];
  var past=valid.filter(function(x){return x.date<startDate;});
  for(var j=0;j<count;j++) {
    var d=new Date(startDate+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+j);
    var ds=d.toISOString().slice(0,10), weekday=d.getUTCDay();
    var group=past.filter(function(x){return new Date(x.date+'T12:00:00Z').getUTCDay()===weekday;}).slice(-8);
    if (group.length<3) {results.push({date:ds,expected:null,lower:null,upper:null,sample:group.length});continue;}
    var vals=group.map(function(x){return omNum_(x.inside_sales);});
    // Give the latest comparable day more weight, while keeping the model explainable.
    var weighted=0,weights=0; vals.forEach(function(v,i){weighted+=v*(i+1);weights+=i+1;});
    var avg=weighted/weights, variance=vals.reduce(function(s,v){return s+Math.pow(v-avg,2);},0)/vals.length;
    var band=Math.min(.5,Math.max(.15,1.28*Math.sqrt(variance)/Math.max(1,avg)));
    results.push({date:ds,expected:omRound_(avg,2),lower:omRound_(Math.max(0,avg*(1-band)),2),upper:omRound_(avg*(1+band),2),sample:group.length});
  }
  return {status:results.some(function(p){return p.expected!==null;})?'baseline':'insufficient',method:'Recency-weighted same-weekday average',required:14,available:valid.length,points:results,note:'Baseline only, not causal. Ranges are heuristic, not calibrated statistical confidence intervals.'};
}

/** Explainable issue prioritization. The level is urgency/relevance, NOT a predicted sales effect. */
function omImpacts_(storeId,signals,events,summary) {
  var out=[],now=Date.now(), today=omToday_();
  function add(type,level,title,evidence,action,source,verified){out.push({type:type,level:level,title:title,evidence:evidence,action:action,source:source,verified:verified,store_id:storeId});}
  signals.filter(function(s){return s.kind==='weather_alert' && (!s.expires_at||Date.parse(s.expires_at)>now);}).slice(-5).forEach(function(s){
    add('Weather',['Extreme','Severe'].indexOf(s.severity)>=0?'high':'medium',s.title,'NWS alert for the configured location; source timestamp '+s.observed_at,
      'Check current NWS details, safety procedures, supplier schedules, and customer access.','NWS',true);
  });
  signals.filter(function(s){return s.kind==='traffic_flow' && now-Date.parse(s.observed_at)<=3*3600000;}).slice(-2).forEach(function(s){
    var m=String(s.details||'').match(/reduction\s+([0-9.]+)%/i),reduction=m?Number(m[1]):null;
    if(reduction!=null&&reduction>=25)add('Traffic',reduction>=45?'high':'medium','Nearby road traffic slower than free flow',
      reduction.toFixed(1)+'% slower than free-flow speed at the matched segment; NOT traffic volume.',
      'Check Google Maps/FL511 and actual store approaches before changing delivery routes.','TomTom',true);
  });
  signals.filter(function(s){return s.kind==='traffic_incident' && now-Date.parse(s.observed_at)<=2*3600000;}).slice(-4).forEach(function(s){
    add('Road incident','medium',s.title,'Recent mapped traffic report within a surrounding box; store entrance impact is not confirmed.',
      'Confirm incident and route effects using FL511 before operational changes.','TomTom',true);
  });
  events.filter(function(e){return e.status==='Active'||(e.start_date && e.start_date<=today && (!e.end_date||e.end_date>=today));}).slice(-7).forEach(function(e){
    add('Planned/local event',e.severity==='High'?'high':'medium',e.title,e.description,
      'Check source and compare historical sales, customer visits and delivery routes.','Store-verified event',!!e.source_url);
  });
  var keywords=/fuel|oil|gasoline|refiner|tobacco|vape|hemp|hurricane|retail|supply|road|closure|construction|tax|fda/i;
  signals.filter(function(s){return s.kind==='news_mention'&&keywords.test(s.title)&&now-Date.parse(s.observed_at)<=48*3600000;}).slice(-5).forEach(function(s){
    add('News watch','info',s.title,'News headline only. Actual applicability and business impact are unverified.',
      'Read the original source and log a verified event only if it applies to your store.','Google News RSS',false);
  });
  if(summary.low_stock_count>0)add('Inventory','medium',summary.low_stock_count+' items at/below reorder point',
    'Calculated from entered on-hand values; accuracy depends on when stock was counted.','Confirm quantities and reorder based on demand.','Store inventory',true);
  if(summary.vendor_variance>0)add('Purchases','medium','Open vendor audit differences',
    'Total absolute unreconciled variance: $'+summary.vendor_variance.toFixed(2)+'.','Verify discounts/credits and request corrections.','Vendor audit',true);
  var order={high:0,medium:1,info:2};return out.sort(function(a,b){return order[a.level]-order[b.level];}).slice(0,30);
}
