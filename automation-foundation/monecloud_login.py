import os
import time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

def main():
    username = os.environ.get("MONECLOUD_USERNAME")
    password = os.environ.get("MONECLOUD_PASSWORD")

    if not username or not password:
        raise SystemExit("Required credentials unavailable.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        try:
            context = browser.new_context()
            page = context.new_page()

            page.goto(
                "https://www.mostedge.com/login",
                wait_until="domcontentloaded",
                timeout=60000
            )

            url = urlsplit(page.url)

            if (url.scheme, url.hostname, url.path) != (
                "https", "www.mostedge.com", "/login"
            ):
                raise SystemExit("Unexpected login page.")

            page.locator('input[name="username"]').fill(username)
            page.locator('input[name="password"]').fill(password)

            page.get_by_role(
                "button", name="LOG IN", exact=True
            ).click()

            for _ in range(45):
                for tab in context.pages:
                    target = urlsplit(tab.url)

                    if (
                        target.scheme == "https"
                        and target.hostname == "monecloud.aboveo.com"
                        and target.path == "/user/puzzleMainPage"
                        and tab.locator(
                            "input[type=password]:visible"
                        ).count() == 0
                    ):
                        print("MoneCloud dashboard reached.")
                        return

                time.sleep(1)

            raise SystemExit(
                "Dashboard not verified. "
                "Check login, MFA or portal redirect."
            )

        except Exception:
            raise SystemExit(
                "Login test failed. Manual review required."
            ) from None

        finally:
            browser.close()

if __name__ == "__main__":
    main()
