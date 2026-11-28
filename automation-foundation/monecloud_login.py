import os
import time
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www.mostedge.com/login"
LOGIN_HOST = "www.mostedge.com"
DASHBOARD_HOST = "monecloud.aboveo.com"
DASHBOARD_PATH = "/user/puzzleMainPage"


def trusted_login_page(page):
    target = urlsplit(page.url)

    return (
        target.scheme == "https"
        and target.netloc == LOGIN_HOST
        and target.path.rstrip("/") == "/login"
    )


def main():

    stage = "INITIALIZATION"

    username = os.environ.get("MONECLOUD_USERNAME")
    password = os.environ.get("MONECLOUD_PASSWORD")

    if not username or not password:
        raise SystemExit("FAIL: Required GitHub secrets unavailable.")

    if os.environ.get("MONECLOUD_ENABLED", "").lower() != "true":
        raise SystemExit("FAIL: MoneCloud automation is disabled.")

    if os.environ.get("AUTOMATION_MODE") != "READ_ONLY":
        raise SystemExit("FAIL: Read-only mode required.")

    print("GitHub credentials available.")
    print("Automation mode: READ_ONLY")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=True)

        try:
            context = browser.new_context(
                accept_downloads=False
            )

            page = context.new_page()

            page.set_default_timeout(15000)

            # ----------------------------------
            # OPEN LOGIN WEBSITE
            # ----------------------------------

            stage = "OPEN_LOGIN_PAGE"

            response = page.goto(
                LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            if response is None or response.status >= 400:
                raise SystemExit("FAIL: Login page unavailable.")

            print("Login page HTTP status:", response.status)

            if not trusted_login_page(page):
                raise SystemExit("FAIL: Unexpected login destination.")

            print("Login destination verified.")

            # ----------------------------------
            # IDENTIFY LOGIN ELEMENTS
            # ----------------------------------

            stage = "LOCATE_LOGIN_FIELDS"

            username_field = page.locator(
                'input[name="username"]:visible'
            )

            password_field = page.locator(
                'input[name="password"]:visible'
            )

            login_button = page.locator(
                'button:has-text("LOG IN"):visible'
            )

            username_field.wait_for(state="visible")
            password_field.wait_for(state="visible")
            login_button.wait_for(state="visible")

            print("Username matches:", username_field.count())
            print("Password matches:", password_field.count())
            print("Login button matches:", login_button.count())

            if username_field.count() != 1:
                raise SystemExit("FAIL: Username selector not unique.")

            if password_field.count() != 1:
                raise SystemExit("FAIL: Password selector not unique.")

            if login_button.count() != 1:
                raise SystemExit("FAIL: Login button selector not unique.")

            if not trusted_login_page(page):
                raise SystemExit("FAIL: Login destination changed.")

            # ----------------------------------
            # ENTER GITHUB SECRET CREDENTIALS
            # ----------------------------------

            stage = "FILL_CREDENTIALS"

            username_field.fill(username)

            if not trusted_login_page(page):
                raise SystemExit("FAIL: Unexpected page change.")

            password_field.fill(password)

            print("Login fields populated securely.")

            # ----------------------------------
            # CORRECTED LOGIN BUTTON
            # ----------------------------------

            stage = "LOGIN_BUTTON"

            if not trusted_login_page(page):
                raise SystemExit("FAIL: Login destination changed.")

            login_button.click(timeout=15000)

            print("Login button clicked.")

            # ----------------------------------
            # VERIFY DASHBOARD ACCESS
            # ----------------------------------

            stage = "VERIFY_DASHBOARD"

            deadline = time.monotonic() + 60

            while time.monotonic() < deadline:

                for tab in context.pages:

                    if tab.is_closed():
                        continue

                    target = urlsplit(tab.url)

                    if (
                        target.scheme == "https"
                        and target.netloc == DASHBOARD_HOST
                        and target.path.rstrip("/") == DASHBOARD_PATH
                    ):

                        tab.wait_for_load_state(
                            "domcontentloaded",
                            timeout=15000
                        )

                        current = urlsplit(tab.url)

                        if (
                            current.scheme == "https"
                            and current.netloc == DASHBOARD_HOST
                            and current.path.rstrip("/") == DASHBOARD_PATH
                            and tab.locator(
                                "input[type=password]:visible"
                            ).count() == 0
                        ):

                            print("============================")
                            print("DASHBOARD ROUTE REACHED")
                            print("MoneCloud dashboard reached.")
                            print("No business records modified.")
                            print("============================")

                            return

                page.wait_for_timeout(1000)

            print("Dashboard route was not verified.")
            print("Check credentials, MFA, CAPTCHA or portal redirect.")

            raise SystemExit(1)

        except Exception as exc:

            print("FAILED STAGE:", stage)
            print("ERROR TYPE:", type(exc).__name__)
            print("Manual review required.")

            raise SystemExit(1) from None

        finally:
            browser.close()


if __name__ == "__main__":
    main()