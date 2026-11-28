from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content('<table><tr><th>Reference</th><th>Amount</th></tr><tr><td>TEST-001</td><td>12.34</td></tr></table>')
            cells = page.locator('table tr').nth(1).locator('td').all_text_contents()
            assert cells == ['TEST-001', '12.34'], 'Synthetic extraction failed'
            print('Synthetic browser extraction passed; no live data accessed.')
        finally:
            browser.close()

if __name__ == '__main__':
    main()
