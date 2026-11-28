import re
from urllib.parse import urlsplit

MODULES = {
    "Sales": ["sales"],
    "Fuel": ["fuel", "gasoline"],
    "Purchases": ["purchase", "purchases"],
    "Inventory": ["inventory", "stock"],
    "Lottery": ["lottery"],
    "Customers": ["customer", "customers"],
    "Vendors": ["vendor", "vendors"],
    "Departments": ["department", "departments"],
    "Pricebook": ["pricebook", "price book"],
    "Shifts": ["shift", "shifts"],
    "Accounting": ["accounting"],
    "Audit": ["audit", "reconciliation"],
    "Reports": ["report", "reports"],
    "Invoices": ["invoice", "invoices"],
    "Expenses": ["expense", "expenses"],
    "Employees": ["employee", "employees"],
    "Products": ["product", "products"],
    "Transactions": ["transaction", "transactions"],
    "Promotions": ["promotion", "discounts"],
    "Locations": ["location", "locations"],
    "Settings": ["settings"],
}


def map_dashboard(page):

    print("OM AI WEBSITE DISCOVERY STARTED")

    page.wait_for_timeout(8000)

    url = urlsplit(page.url)

    if (
        url.scheme != "https"
        or url.netloc != "monecloud.aboveo.com"
        or url.path.rstrip("/") != "/user/puzzleMainPage"
    ):
        raise RuntimeError("Unexpected dashboard destination")

    if page.locator("input[type=password]:visible").count():
        raise RuntimeError("Login screen detected")

    elements = page.locator(
        'a:visible, button:visible, '
        '[role="menuitem"]:visible, '
        '[role="tab"]:visible, '
        '[role="button"]:visible'
    )

    labels = elements.evaluate_all("""
        elements => elements.slice(0, 3000).map(e =>
            (e.getAttribute("aria-label") || e.innerText || "")
            .trim().slice(0, 120)
        )
    """)

    detected = set()

    for label in labels:

        normalized = re.sub(
            r"\s+", " ", label.lower()
        ).strip()

        for module, aliases in MODULES.items():

            if any(
                re.search(
                    r"\b" + re.escape(alias) + r"\b",
                    normalized
                )
                for alias in aliases
            ):
                detected.add(module)

    print("Visible navigation elements:", len(labels))

    print("================================")
    print("MODULE DISCOVERY RESULTS")
    print("================================")

    for module in MODULES:

        status = (
            "DETECTED"
            if module in detected
            else "NOT YET DETECTED"
        )

        print(f"{module}: {status}")

    print("================================")
    print("Detected module candidates:", len(detected))
    print("Business records exported: 0")
    print("Business controls clicked: 0")
    print("Private URLs exported: 0")

    if not detected - {"Locations", "Settings"}:
        raise RuntimeError("Business navigation not detected")

    print("MONECLOUD MAPPING TEST COMPLETED")
    print("Protected report access: NOT YET VERIFIED")
