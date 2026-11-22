/** Record proof of server-side source checks. Called by scheduled refresh, never by browser. */
function omRecordServiceJobs_(storeId,statuses){
  var map={
   'NWS weather':{job_id:'weather_refresh',name:'NWS weather & alert ingestion',owner:'OM Radar',max_age_hours:3},
   'TomTom traffic':{job_id:'traffic_refresh',name:'TomTom traffic API update',owner:'OM Radar',max_age_hours:3},
   'Google News RSS':{job_id:'news_feed_refresh',name:'News headlines feed ingestion',owner:'OM Radar',max_age_hours:3}
  };
  var current={};omForStore_(omRead_('ServiceJobs',500),storeId).forEach(function(r){current[r.id]=true;});
  omLock_(function(){
    (statuses||[]).forEach(function(s){
      var def=map[s.source];if(!def)return;
      var id=storeId+'|'+def.job_id, state=s.status==='ok'?'healthy':s.status==='not_configured'?'not_connected':s.status==='error'?'failed':'needs_review';
      var row={id:id,store_id:storeId,job_id:def.job_id,name:def.name,provider:s.source,owner:def.owner,
       state:state,last_run:omNow_(),age_hours:0,max_age_hours:def.max_age_hours,
       detail:omClean_(s.detail,180),next_action:state==='healthy'?'Review result quality in source tab.':
         state==='not_connected'?'Configure an authorized source/API key.':'Review provider error and retry after the source becomes available.',
       evidence_ref:'',checked_at:omNow_()};
      if(current[id])omPatch_('ServiceJobs',id,row);else omAppend_('ServiceJobs',row);
    });
  });
}
