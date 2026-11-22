"""Responsive surveillance tab smoke test: no JS errors at phone width."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
html=(root/'preview/OM-AI-preview.html').read_text()
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage'])
    page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded')
    page.locator('.mobile-nav [data-nav="cameras"]').click()
    assert page.locator('.cam-card').count()==14
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1'), 'horizontal page overflow'
    assert not errors, errors
    page.screenshot(path=str(root/'preview/OM-AI-cameras-mobile.png'),full_page=True)
    browser.close()
print('PASS: mobile camera module + no horizontal overflow')
