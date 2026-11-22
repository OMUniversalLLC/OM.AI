/** Run once from the Apps Script editor, after setting OWNER_EMAIL in Script Properties. */
function setupOmAi() {
  omOwner_();
  var props=omProps_();
  var id=props.getProperty('OM_AI_SHEET_ID');
  var db=id ? SpreadsheetApp.openById(id) : SpreadsheetApp.create('OM AI — Private Intelligence Database');
  if (!id) props.setProperty('OM_AI_SHEET_ID',db.getId());
  Object.keys(OM_SCHEMA).forEach(function(name) {
    var sh=db.getSheetByName(name) || db.insertSheet(name);
    var schema=OM_SCHEMA[name];
    if (sh.getLastRow()===0) sh.getRange(1,1,1,schema.length).setValues([schema]);
    else {
      var current=sh.getRange(1,1,1,schema.length).getValues()[0];
      if (JSON.stringify(current)!==JSON.stringify(schema)) throw new Error('Schema conflict on '+name+'. Use a new database or perform a migration.');
    }
    sh.setFrozenRows(1);
    sh.getRange(1,1,1,schema.length).setBackground('#172642').setFontColor('#ffffff').setFontWeight('bold');
    sh.setColumnWidths(1,schema.length,130);
    sh.getRange(1,1,sh.getMaxRows(),schema.length).setVerticalAlignment('middle');
  });
  if (omRead_('Users').length===0) omAppend_('Users',{email:omActor_(),name:'Owner',role:'Admin',store_ids:'QUICKC,INVERNESS,VAPESTORE',active:'Yes'});
  if (omRead_('Stores').length===0) {
    omAppend_('Stores',{store_id:'QUICKC',name:'Quick-C SUNOCO — Plant City',address:'',latitude:'',longitude:'',timezone:'America/New_York',active:'Yes'});
    omAppend_('Stores',{store_id:'INVERNESS',name:'Inverness Store',address:'Set your exact address',latitude:'',longitude:'',timezone:'America/New_York',active:'Yes'});
    omAppend_('Stores',{store_id:'VAPESTORE',name:'Puff Republic / Vape Store',address:'Set your exact address',latitude:'',longitude:'',timezone:'America/New_York',active:'Yes'});
  }
  // Protect role assignments, store settings, and audit history from ordinary Sheet editors.
  ['Users','Stores','AuditLog'].forEach(function(name) {
    var sheet=db.getSheetByName(name);
    var protections=sheet.getProtections(SpreadsheetApp.ProtectionType.SHEET);
    var protection=protections[0]||sheet.protect().setDescription('OM AI owner-only: '+name);
    protection.setWarningOnly(false);
    protection.addEditor(omActor_());
    var others=protection.getEditors().filter(function(u){return String(u.getEmail()).toLowerCase()!==omActor_();});
    if(others.length)protection.removeEditors(others);
    if(protection.canDomainEdit())protection.setDomainEdit(false);
  });
  omSeedFuelSources_();
  omSeedCameras_();
  // Network sheets are created empty; no devices or camera streams are claimed online.
  Logger.log('OM AI database ready: '+db.getUrl());
  return db.getUrl();
}

/** Install an hourly source refresh as the owner. No external calls are made until this runs. */
function installOmAiHourlyMonitoring() {
  omOwner_();
  ScriptApp.getProjectTriggers().filter(function(t){return t.getHandlerFunction()==='scheduledOmAiRefresh';}).forEach(ScriptApp.deleteTrigger);
  ScriptApp.newTrigger('scheduledOmAiRefresh').timeBased().everyHours(1).create();
  return 'Hourly monitoring enabled';
}

function removeOmAiHourlyMonitoring() {
  omOwner_();
  ScriptApp.getProjectTriggers().filter(function(t){return t.getHandlerFunction()==='scheduledOmAiRefresh';}).forEach(ScriptApp.deleteTrigger);
  return 'Hourly monitoring disabled';
}

/** Configurable key names: TOMTOM_API_KEY, GEMINI_API_KEY, GEMINI_MODEL, DIGEST_EMAIL. Do not put keys into Sheets. */
function getOmAiSetupStatus() {
  omOwner_();
  var p=omProps_();
  return {database:p.getProperty('OM_AI_SHEET_ID')?'ready':'not configured',tomtom:!!p.getProperty('TOMTOM_API_KEY'),gemini:!!p.getProperty('GEMINI_API_KEY'),owner:p.getProperty('OWNER_EMAIL')};
}
