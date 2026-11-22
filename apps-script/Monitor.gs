/** Live-source adapters. No API key or response => NEVER show zero incidents as if verified. */
function scheduledOmAiRefresh() {
  omOwner_();
  omRead_('Stores').filter(function(x){return String(x.active).toLowerCase()==='yes';}).forEach(function(s){
    try{omRefreshSources_(s);}catch(e){console.error('OM AI refresh '+s.store_id+': '+e.message);}
  });
  var email=omProps_().getProperty('DIGEST_EMAIL');
  if(email && /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)){
    // Email digest is intentionally NOT sent each hour; use scheduledOmAiDigest daily.
  }
}
function refreshOmAiSources(storeId) {
  var user=omAuth_();
  if(user.role==='Viewer')throw new Error('Only Admins/Managers can refresh external sources.');
  var store=omStoreAccess_(user,storeId,true);
  return omRefreshSources_(store);
}
function omRefreshSources_(store) {
  var status={store_id:store.store_id,updated_at:omNow_(),sources:[]};
  if(!isFinite(Number(store.latitude))||!Number(store.latitude)||!isFinite(Number(store.longitude))||!Number(store.longitude)){
    status.sources.push({source:'Location',status:'not_configured',detail:'Enter verified coordinates in Stores sheet.'});
    return status;
  }
  var lat=Number(store.latitude),lon=Number(store.longitude);
  try{status.sources.push(omWeather_(store,lat,lon));}catch(e){status.sources.push({source:'NWS weather',status:'error',detail:e.message});}
  if(omProps_().getProperty('TOMTOM_API_KEY')){
    try{status.sources.push(omTomTom_(store,lat,lon));}catch(e){status.sources.push({source:'TomTom traffic',status:'error',detail:e.message});}
  } else status.sources.push({source:'TomTom traffic',status:'not_configured',detail:'Set TOMTOM_API_KEY in Script Properties.'});
  try{status.sources.push(omNews_(store));}catch(e){status.sources.push({source:'Google News RSS',status:'error',detail:e.message});}
  try{omRecordServiceJobs_(store.store_id,status.sources);}catch(e){console.error('Source health receipt: '+e.message);}
  return status;
}
function omSaveSignals_(storeId,incoming) {
  if(!incoming.length)return 0;
  return omLock_(function(){
    var previous={};omForStore_(omRead_('Signals',3000),storeId).forEach(function(x){previous[x.source_key]=true;});
    var added=0;
    incoming.forEach(function(x){
      if(!x.source_key||previous[x.source_key])return;
      previous[x.source_key]=true;x.id=omUid_('SIG');x.store_id=storeId;
      ['title','details'].forEach(function(k){x[k]=omClean_(x[k],k==='title'?220:750);});
      x.source_url=omUrl_(x.source_url);
      omAppend_('Signals',x);added++;
    });
    return added;
  });
}
function omWeather_(store,lat,lon){
  var head={'Accept':'application/geo+json','User-Agent':'OM-AI-Store-Monitor/1.0 (business weather monitoring; contact via owner account)'};
  var point=omJson_('https://api.weather.gov/points/'+lat.toFixed(4)+','+lon.toFixed(4),head);
  var hourlyUrl=point.properties && point.properties.forecastHourly;
  if(!hourlyUrl)throw new Error('NWS point did not return a forecast endpoint.');
  var hourly=omJson_(hourlyUrl,head);
  var period=(hourly.properties&&hourly.properties.periods||[])[0];
  var notices=omJson_('https://api.weather.gov/alerts/active?point='+lat.toFixed(4)+','+lon.toFixed(4),head);
  var now=omNow_(), signals=[];
  if(period){
    var chance=(period.probabilityOfPrecipitation||{}).value;
    var stamp=String(period.startTime||now);
    signals.push({source:'NWS',kind:'weather_forecast',observed_at:now,title:'Hourly forecast: '+period.shortForecast,
      value:period.temperature,unit:period.temperatureUnit||'F',details:'Forecast starts '+stamp+' · Rain chance '+(chance==null?'not provided':chance+'%')+' · '+String(period.detailedForecast||period.shortForecast||''),
      source_url:'https://forecast.weather.gov/',source_key:'nws-forecast|'+store.store_id+'|'+stamp});
  }
  (notices.features||[]).slice(0,8).forEach(function(a){var p=a.properties||{};
    signals.push({source:'NWS',kind:'weather_alert',observed_at:now,title:String(p.event||'Weather alert'),value:'',unit:'',
      details:String(p.headline||p.description||'Weather alert').slice(0,700),source_url:omUrl_(p.uri||p['@id']||'https://alerts.weather.gov/'),
      source_key:'nws-alert|'+String(p.id||a.id||p.sent||''),expires_at:String(p.expires||''),severity:String(p.severity||'Moderate')});
  });
  var added=omSaveSignals_(store.store_id,signals);
  return {source:'NWS weather',status:'ok',detail:'Forecast '+(period?period.shortForecast:'unavailable')+' · active alerts: '+(notices.features||[]).length,added:added,observed_at:now};
}
function omTomTom_(store,lat,lon) {
  var key=omProps_().getProperty('TOMTOM_API_KEY');if(!key)return {source:'TomTom traffic',status:'not_configured'};
  var base='https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json?point='+lat+','+lon+'&unit=KMPH&key='+encodeURIComponent(key);
  var flow=omJson_(base), segment=flow.flowSegmentData||{};
  var now=omNow_(), signals=[];
  if(segment.currentSpeed!=null) {
    var delay=omNum_(segment.freeFlowSpeed)>0?omRound_(Math.max(0,100*(1-omNum_(segment.currentSpeed)/omNum_(segment.freeFlowSpeed))),1):null;
    signals.push({source:'TomTom',kind:'traffic_flow',observed_at:now,title:'Nearby road speed',value:segment.currentSpeed,unit:'km/h',
      details:'Free-flow speed '+segment.freeFlowSpeed+' km/h; reduction '+(delay==null?'unknown':delay+'%')+'. This measures speed on a nearby mapped segment, NOT vehicle count.',
      source_url:'https://www.tomtom.com/traffic-index/',source_key:'tomtom-flow|'+store.store_id+'|'+now.slice(0,13)});
  }
  // Incident service v5: optional; each failure is reported separately instead of disguised as no incidents.
  var latdelta=4/69, londelta=4/(69*Math.max(0.2,Math.cos(lat*Math.PI/180)));
  var bbox=[lon-londelta,lat-latdelta,lon+londelta,lat+latdelta].map(function(n){return n.toFixed(5);}).join(',');
  var fields='{incidents{type,properties{id,iconCategory,magnitudeOfDelay,events{description,code},startTime,endTime,from,to,length,delay,roadNumbers}}}';
  var incidentUrl='https://api.tomtom.com/traffic/services/5/incidentDetails?bbox='+bbox+'&fields='+encodeURIComponent(fields)+'&language=en-US&timeValidityFilter=present&key='+encodeURIComponent(key);
  var incidentStatus='';
  try {
    var response=omJson_(incidentUrl);
    var incidents=response.incidents||[];
    incidents.slice(0,15).forEach(function(incident){
      var p=incident.properties||{}, first=(p.events||[])[0]||{};
      signals.push({source:'TomTom',kind:'traffic_incident',observed_at:now,title:'Traffic incident: '+(first.description||p.from||'road issue'),
        value:p.delay||0,unit:'seconds delay',details:'From '+(p.from||'unknown')+' to '+(p.to||'unknown')+' · '+(first.description||'Traffic incident'),
        source_url:'https://www.tomtom.com/traffic-index/',source_key:'tomtom-incident|'+store.store_id+'|'+(p.id||p.startTime||first.description)});
    });
    incidentStatus=incidents.length+' incident(s) reported in approx 4-mile box';
  }catch(e){incidentStatus='Incident feed unavailable: '+e.message;}
  return {source:'TomTom traffic',status:segment.currentSpeed!=null?'ok':'partial',detail:(segment.currentSpeed==null?'Speed unavailable':segment.currentSpeed+' km/h near store')+' · '+incidentStatus,
    added:omSaveSignals_(store.store_id,signals),observed_at:now};
}
function omNews_(store){
  var local=(store.store_id==='QUICKC')?['Plant City Florida road closures construction','Plant City Florida gas station business news']:['Florida convenience store fuel supply regulations'];
  var queries=local.concat(['US gasoline supply disruption refineries gas stations','FDA tobacco vaping retail rules USA']);
  var signals=[],now=omNow_();
  queries.forEach(function(q){
    var url='https://news.google.com/rss/search?q='+encodeURIComponent(q+' when:7d')+'&hl=en-US&gl=US&ceid=US:en';
    var res=UrlFetchApp.fetch(url,{muteHttpExceptions:true,timeout:18000});
    if(res.getResponseCode()!==200)throw new Error('News feed HTTP '+res.getResponseCode());
    var xml=XmlService.parse(res.getContentText());
    var channel=xml.getRootElement().getChild('channel');if(!channel)return;
    channel.getChildren('item').slice(0,7).forEach(function(item){
      var title=String(item.getChildText('title')||'').trim(), link=String(item.getChildText('link')||'');
      var pub=String(item.getChildText('pubDate')||'');
      if(!title)return;
      signals.push({source:'Google News RSS',kind:'news_mention',observed_at:now,title:title,value:'',unit:'',
        details:'News mention · '+q+' · Published: '+pub+'. Verify the underlying article before acting.',source_url:link,
        source_key:'news|'+store.store_id+'|'+Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,title)).slice(0,22)});
    });
  });
  return {source:'Google News RSS',status:'ok',detail:signals.length+' mentions fetched (not verified incidents)',added:omSaveSignals_(store.store_id,signals),observed_at:now};
}

/** Optional one-email-per-day digest, run with a separate daily trigger configured by the owner. */
function scheduledOmAiDigest(){
  omOwner_();
  var addr=String(omProps_().getProperty('DIGEST_EMAIL')||'');
  if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(addr))return;
  var today=omToday_(), key='DIGEST_SENT_DATE';
  if(omProps_().getProperty(key)===today)return;
  var lines=['OM AI daily management summary — '+today];
  omRead_('Stores').filter(function(s){return String(s.active).toLowerCase()==='yes';}).forEach(function(s){
    var sales=omForStore_(omRead_('Sales',2000),s.store_id),tasks=omForStore_(omRead_('Tasks',2000),s.store_id);
    var summary=omSummary_(sales,[],[],tasks,[],[]);
    lines.push(s.name+': latest sales '+(summary.latest_sales==null?'not connected':'$'+summary.latest_sales.toFixed(2))+' ('+(summary.latest_date||'no date')+'), open tasks '+summary.open_tasks);
  });
  MailApp.sendEmail(addr,'OM AI daily digest — '+today,lines.join('\n'));
  omProps_().setProperty(key,today);
}
