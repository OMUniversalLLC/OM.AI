"""Optional smoke test. Requires playwright + Chromium (not needed for deployment)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
html=(root/'preview/OM-AI-preview.html').read_text()
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-dev-shm-usage','--disable-background-networking'])
    page=b.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded',timeout=10000)
    assert 'Business clarity' in page.locator('h1').inner_text()
    for key in ['radar','impact','insights','predict','alerts','watch','control','advisor','finance','fuel','cameras','wifi','compliance','settings','overview']:
        page.locator(f'.sidebar [data-nav="{key}"]').click()
        assert page.locator('#page-title').inner_text()
    page.locator('.sidebar [data-nav="fuel"]').click()
    assert page.get_by_text('GasBuddy competitor prices').count() > 0
    assert page.get_by_text('AAA market averages').count() > 0
    assert page.get_by_text('MostEdge store fuel report').count() > 0
    page.locator('.sidebar [data-nav="cameras"]').click()
    assert page.locator('.cam-card').count() == 14
    assert '14-CAMERA' in page.locator('#view').inner_text()
    page.locator('.sidebar [data-nav="wifi"]').click()
    assert 'Network agent' in page.locator('#view').inner_text()
    assert page.locator('.net-cam').count() == 14
    assert 'DEMO DATA ONLY' in page.locator('#view').inner_text()
    assert not errors,errors
    page.screenshot(path=str(root/'preview/preview-screenshot.png'),full_page=True)
    b.close()
print('PASS: desktop browser tabs rendered with no JavaScript page errors')
