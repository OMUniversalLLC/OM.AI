"""Read-only inventory discovery. Never print product values or page contents."""
import os
import time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

HOST = 'monecloud.aboveo.com'
DASH = '/user/puzzleMainPage'
INVENTORY = '/pricebook/inventory'

SCAN = r'''() => {
 const norm = s => String(s || '').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
 const visible = e => !!e.getClientRects().length && getComputedStyle(e).visibility === 'visible';
 const groups = {upc:['upc','upc code','barcode','bar code','gtin'], name:['item name','product name','description','item description','product description'], price:['price','retail price','retail','selling price','sale price']};
 const headers = cells => { const labels=cells.map(c=>norm(c.innerText)); const m={}; for(const [k,a] of Object.entries(groups)){const hits=labels.map((v,i)=>a.includes(v)?i:-1).filter(i=>i>=0);if(hits.length!==1)return null;m[k]=hits[0];}return m; };
 const cellValue = c => {const inputs=Array.from(c.querySelectorAll('input:not([type=hidden]):not([type=checkbox]):not([type=radio]):not([type=button]), textarea')).filter(visible);return inputs.length===1?inputs[0].value.trim():c.innerText.trim();};
 const validCells=(cells,n)=>cells.length===n && cells.every(c=>(c.colSpan||1)===1&&(c.rowSpan||1)===1);
 const bodyRows=t=>Array.from(t.tBodies).flatMap(b=>Array.from(b.rows)).filter(visible);
 const results=[]; const seenRows=new Set(); let matched=0, split=0, aria=0;
 const add=(rows,map,n,mode)=>{const eligible=rows.filter(r=>!seenRows.has(r.node)&&validCells(r.cells,n));if(!eligible.length)return;for(const r of eligible)seenRows.add(r.node);results.push({rows:eligible,map,mode});};
 for(const t of document.querySelectorAll('table')){
  if(!visible(t)||!t.tHead)continue;
  for(const h of Array.from(t.tHead.rows)){
   const cells=Array.from(h.cells), m=headers(cells); if(!m||!validCells(cells,cells.length))continue; matched++;
   const n=cells.length, own=bodyRows(t).map(node=>({node,cells:Array.from(node.cells)}));
   add(own,m,n,'html');
   // Link only through a recognized widget wrapper, never by table position alone.
   if(!own.some(r=>validCells(r.cells,n))){
    const wrap=t.closest('.dataTables_scroll,.dt-scroll,.k-grid,.ui-jqgrid,.ui-datatable-scrollable,.ag-root-wrapper');
    if(wrap){const candidates=Array.from(wrap.querySelectorAll('table')).filter(b=>b!==t&&visible(b)&&bodyRows(b).some(r=>validCells(Array.from(r.cells),n))&&(!b.tHead||Array.from(b.tHead.rows).every(hr=>{const hc=Array.from(hr.cells);return hc.every(c=>!norm(c.innerText))||JSON.stringify(headers(hc))===JSON.stringify(m);})));if(candidates.length===1){split++;add(bodyRows(candidates[0]).map(node=>({node,cells:Array.from(node.cells)})),m,n,'split');}}
   }
   break;
  }
 }
 for(const grid of document.querySelectorAll('[role=grid],[role=table]')){
  if(!visible(grid)||grid.tagName==='TABLE')continue;
  const rows=Array.from(grid.querySelectorAll('[role=row]')).filter(r=>visible(r)&&r.closest('[role=grid],[role=table]')===grid);
  const header=rows.map(r=>Array.from(r.querySelectorAll('[role=columnheader]'))).find(c=>c.length&&headers(c)); if(!header)continue;
  const m=headers(header), n=header.length;
  const idx=header.map(c=>c.getAttribute('aria-colindex')); if(idx.some(x=>x!==null)&&!idx.every((x,i)=>Number(x)===i+1))continue;
  matched++;aria++;
  const body=rows.map(node=>({node,cells:Array.from(node.querySelectorAll('[role=gridcell],[role=cell]'))})).filter(r=>r.cells.every((c,i)=>!c.hasAttribute('aria-colindex')||Number(c.getAttribute('aria-colindex'))===i+1)); add(body,m,n,'aria');
 }
 const summary={matched, populated:results.length, split, aria, sampled:0, upc:0, name:0, price:0, complete:0, duplicates:0, leadingZeros:0, placeholderRows:0};
 if(results.length!==1)return summary;
 const seen=new Set(); const {rows,map}=results[0];
 for(const r of rows.slice(0,50)){
  const upc=cellValue(r.cells[map.upc]), name=cellValue(r.cells[map.name]), raw=cellValue(r.cells[map.price]);
  if(!upc&&!name&&!raw){summary.placeholderRows++;continue;}
  summary.sampled++;
  const goodUPC=/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(upc), goodName=!!name&&!/^(no data|no records|no results|loading)$/i.test(name), goodPrice=/^\$?\s*(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?$/.test(raw);
  if(goodUPC){summary.upc++;if(upc.startsWith('0'))summary.leadingZeros++;if(seen.has(upc))summary.duplicates++;seen.add(upc);}
  if(goodName)summary.name++;if(goodPrice)summary.price++;if(goodUPC&&goodName&&goodPrice)summary.complete++;
 }
 return summary;
}'''

CONTROLS = r'''store => {
 const vis=e=>!!e.getClientRects().length&&getComputedStyle(e).visibility==='visible';
 const label=e=>[e.name,e.id,e.getAttribute('aria-label'),e.getAttribute('placeholder'),...Array.from(e.labels||[]).map(l=>l.innerText)].filter(Boolean).join(' ').replace(/([a-z])([A-Z])/g,'$1 $2').toLowerCase().replace(/[^a-z0-9]+/g,' ');
 const selects=Array.from(document.querySelectorAll('select'));
 const filters={store:0,category:0,department:0,vendor:0,other:0,placeholders:0,textInputs:0,loadButtons:0}; const matches=[];
 for(let i=0;i<selects.length;i++){const e=selects[i];if(!vis(e)||e.disabled)continue;const l=label(e);let k='other';for(const [name,regex] of Object.entries({store:/\b(location|store|site)\b/,category:/\bcategory\b/,department:/\bdepartment\b/,vendor:/\bvendor\b/})){if(regex.test(l)){k=name;break;}}filters[k]++; const opt=e.selectedOptions[0];if(!opt||!opt.value||/^(select|choose|please select)\b/i.test(opt.textContent.trim()))filters.placeholders++;
 if(k==='store'&&store&&!e.multiple){const opts=Array.from(e.options).filter(o=>!o.disabled&&(o.value.trim()===store||o.textContent.trim()===store||new RegExp('^'+store+'\\s*[-:–]').test(o.textContent.trim())));if(opts.length===1)matches.push({index:i,value:opts[0].value,selected:opts[0].selected});}}
 filters.textInputs=Array.from(document.querySelectorAll('input[type=text],input[type=search]')).filter(vis).length;
 const buttons=Array.from(document.querySelectorAll('button,input[type=button]'));
 // Only explicit, inventory-specific read operations; no generic Go/Submit/Save.
 const load=[];for(let i=0;i<buttons.length;i++){const b=buttons[i];if(!vis(b)||b.disabled||b.type!=='button')continue;const t=(b.innerText||b.value||b.getAttribute('aria-label')||'').trim().toLowerCase().replace(/\s+/g,' ');if(['search inventory','load inventory','view inventory','show inventory','filter inventory'].includes(t))load.push(i);}
 filters.loadButtons=load.length;
 return {filters,matches,load};
}'''

def trusted(page, path):
    u=urlsplit(page.url)
    return u.scheme=='https' and u.netloc==HOST and u.path.rstrip('/')==path and not page.is_closed()


def require_page(page,path):
    if not trusted(page,path) or page.locator('input[type=password]:visible').count():
        raise RuntimeError('Unexpected page or authentication required')


def select_store(page,path,store):
    require_page(page,path)
    info=page.evaluate(CONTROLS,store)
    for key,val in info['filters'].items(): print(f'Filter {key}: {val}')
    matches=info['matches']
    print('Exact store filter matches:',len(matches))
    if len(matches)!=1:return False
    match=matches[0]
    if not match['selected']:
        # Recheck live DOM before changing the uniquely identified report filter.
        current=page.evaluate(CONTROLS,store)['matches']
        if current!=matches:return False
        page.locator('select').nth(match['index']).select_option(value=match['value'],timeout=10000)
        page.wait_for_timeout(2500)
        require_page(page,path)
    verified=page.evaluate(CONTROLS,store)['matches']
    return len(verified)==1 and verified[0]['selected']


def inspect_inventory(dashboard):
    store=os.environ.get('MONECLOUD_STORE_ID','').strip()
    if not store.isascii() or not store.isdigit(): raise RuntimeError('Store identifier missing or invalid')
    print('PHASE 6C INVENTORY VALIDATION STARTED')
    require_page(dashboard,DASH)
    dashboard_store=select_store(dashboard,DASH,store)
    print('Dashboard store filter confirmed:',dashboard_store)
    # Use same tab so tab-scoped session state survives navigation.
    response=dashboard.goto('https://'+HOST+INVENTORY,wait_until='domcontentloaded',timeout=60000)
    if response is None or response.status>=400:raise RuntimeError('Inventory page unavailable')
    print('Inventory HTTP status:',response.status)
    dashboard.wait_for_timeout(3000)
    require_page(dashboard,INVENTORY)
    inventory_store=select_store(dashboard,INVENTORY,store)
    print('Inventory store filter confirmed:',inventory_store)
    def poll(seconds):
        deadline=time.monotonic()+seconds
        while True:
            require_page(dashboard,INVENTORY)
            r=dashboard.evaluate(SCAN)
            if r['sampled']>0 or time.monotonic()>=deadline:return r
            dashboard.wait_for_timeout(2000)
    r=poll(20)
    if not r['sampled'] and inventory_store:
        controls=dashboard.evaluate(CONTROLS,store)
        if len(controls['load'])==1:
            # Only a uniquely identified, inventory-specific button after store confirmation.
            dashboard.locator('button,input[type=button]').nth(controls['load'][0]).click(timeout=10000)
            print('Inventory-specific load control clicked: 1')
            r=poll(35)
    for key,val in r.items():print(f'Inventory {key}: {val}')
    print('Raw inventory records exported: 0')
    if r['populated']!=1 or not r['sampled'] or not r['complete']:
        print('PHASE 6C RESULT: BLOCKED - inventory records not verified')
        raise RuntimeError('Inventory loading or layout still unresolved')
    if r['complete']!=r['sampled']:
        print('PHASE 6C RESULT: PARTIAL - invalid or incomplete rows')
        raise RuntimeError('Inventory sample not fully validated')
    if not inventory_store:
        print('PHASE 6C RESULT: PARTIAL - sample valid but inventory store not independently verified')
        raise RuntimeError('Store verification still required')
    print('PHASE 6C RESULT: PASSED - validated sample for selected store')


def self_test():
    options={'headless':True}
    if os.environ.get('OM_TEST_CHROMIUM'):options['executable_path']=os.environ['OM_TEST_CHROMIUM']
    with sync_playwright() as p:
        browser=p.chromium.launch(**options)
        try:
            page=browser.new_page()
            head='<thead><tr><th>UPC Code</th><th>Item Name</th><th>Retail Price</th></tr></thead>'
            body='<tbody><tr><td>001234567890</td><td>Test product</td><td><input value="$4.99"></td></tr></tbody>'
            for html in ['<table>'+head+body+'</table>', '<div class="dataTables_scroll"><table>'+head+'</table><table>'+body+'</table></div>', '<div role="grid"><div role="row"><span role="columnheader">UPC Code</span><span role="columnheader">Item Name</span><span role="columnheader">Retail Price</span></div><div role="row"><span role="gridcell">001234567890</span><span role="gridcell">Test product</span><span role="gridcell">$4.99</span></div></div>']:
                page.set_content(html);r=page.evaluate(SCAN);assert r['complete']==1 and r['leadingZeros']==1,r
            page.set_content('<table>'+head+'</table><table>'+body+'</table>');assert page.evaluate(SCAN)['complete']==0
            page.set_content('<table>'+head+body+'</table><table>'+head+body+'</table>');assert page.evaluate(SCAN)['populated']==2 and page.evaluate(SCAN)['complete']==0
            page.set_content('<label>Store<select id="store"><option value="">Select</option><option value="123456">Test store</option></select></label><button type="button">Load Inventory</button><button type="button">Save</button>');c=page.evaluate(CONTROLS,'123456');assert len(c['matches'])==1 and len(c['load'])==1 and c['filters']['placeholders']==1,c
            print('Synthetic tests passed: single table, split table, ARIA grid, unrelated tables, ambiguous tables, store filter and load control.')
        finally:browser.close()

if __name__=='__main__':self_test()
