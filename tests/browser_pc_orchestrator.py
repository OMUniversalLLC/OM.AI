"""Browser regression test for new modules; demo input only."""
from pathlib import Path
from shutil import which
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as pw:
 options={'headless':True}
 if which('chromium'):
  options['executable_path']=which('chromium')
  options['args']=['--no-sandbox']
 browser=pw.chromium.launch(**options)
 for width,height in [(1440,900),(390,844)]:
  page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
  failures=[]
  page.on('pageerror',lambda err:failures.append(str(err)))
  page.set_content((root/'preview/OM-AI-preview.html').read_text(encoding='utf-8'),wait_until='domcontentloaded')
  page.wait_for_selector('.nav-btn[data-nav="pc"]',state='attached')
  page.locator(('.mobile-nav' if width<500 else '.sidebar')+' .nav-btn[data-nav="pc"]').click(timeout=7000)
  assert page.locator('#view').get_by_text('OM PC Intelligence').count()>0
  assert page.locator('#view').get_by_text('CPU temperature',exact=True).count()>0
  assert page.locator('#view').get_by_text('Not measured').count()>0
  assert page.locator('#view').get_by_text('Safe optimization policy:').count()>0
  page.locator(('.mobile-nav' if width<500 else '.sidebar')+' .nav-btn[data-nav="orchestrator"]').click(timeout=7000)
  assert page.locator('#view').get_by_text('OM Orchestrator').count()>0
  assert page.locator('#view').get_by_text('GasBuddy local price verification').count()>0
  assert page.locator('#view').get_by_text('MostEdge authorized store report').count()>0
  assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'Horizontal overflow at '+str(width)
  assert not failures,failures
  page.screenshot(path=str(root/'preview'/('OM-AI-PC-Orchestrator-mobile.png' if width<500 else 'OM-AI-PC-Orchestrator-desktop.png')),full_page=True)
  page.close()
 browser.close()
print('PASS: desktop/mobile OM PC & Orchestrator, no horizontal overflow, no JS exceptions')
