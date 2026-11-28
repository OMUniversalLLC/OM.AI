import re
from urllib.parse import urlsplit

from monecloud_mapper import MODULES
from monecloud_inventory_v2 import inspect_inventory

HOST = "monecloud.aboveo.com"
INVENTORY_PATH = "/pricebook/inventory"

SAFE_HEADERS = {
    "UPC": ["upc", "barcode"],
    "Product name": ["item name", "product name", "description"],
    "Category": ["category", "department"],
    "Inventory": ["inventory", "current inv", "quantity"],
    "Cost": ["cost", "cur cost"],
    "Retail price": ["price", "retail"],
    "Margin": ["margin"],
    "Vendor": ["vendor", "supplier"],
    "Discount": ["discount", "rebate"],
    "Order quantity": ["order"],
}


def trusted(page, path=None):
    target = urlsplit(page.url)

    return (
        target.scheme == "https"
        and target.netloc == HOST
        and (
            path is None
            or target.path.rstrip("/") == path
        )
    )


def matches(text, words):
    return any(
        re.search(
            r"\b" + re.escape(word) + r"\b",
            text.lower()
        )
        for word in words
    )


def navigation_inventory(page):

    elements = page.locator(
        'a, button, [role="menuitem"], '
        '[role="tab"], [role="button"]'
    )

    return elements.evaluate_all("""
        elements => elements.slice(0, 5000).map(e => ({
            label: (
                e.getAttribute("aria-label")
                || e.innerText
                || e.textContent
                || ""
            ).trim().slice(0, 160),
            tag: e.tagName.toLowerCase(),
            visible: e.getClientRects().length > 0
                && getComputedStyle(e).visibility !== "hidden",
            href: e.tagName === "A" ? e.href : "",
            expandable: e.hasAttribute("aria-expanded")
                || e.getAttribute("aria-haspopup") === "true"
        }))
    """)


def inspect_navigation(page):

    if not trusted(page, "/user/puzzleMainPage"):
        raise RuntimeError("Unexpected dashboard destination")

    items = navigation_inventory(page)

    print("================================")
    print("DEEP NAVIGATION ANALYSIS")
    print("================================")

    print("Navigation elements:", len(items))
    print("Visible elements:", sum(x["visible"] for x in items))
    print("Hidden candidates:", sum(not x["visible"] for x in items))
    print("Expandable controls:", sum(x["expandable"] for x in items))

    destinations = set()

    for item in items:

        target = urlsplit(item["href"])

        if (
            target.scheme == "https"
            and target.netloc == HOST
        ):
            destinations.add(target.path)

    print("Unique internal path candidates:", len(destinations))

    for module, aliases in MODULES.items():

        candidates = [
            item for item in items
            if matches(item["label"], aliases)
        ]

        visible = sum(
            item["visible"] for item in candidates
        )

        hidden = len(candidates) - visible

        print(
            f"{module}: "
            f"visible={visible}, hidden={hidden}"
        )

    print(
        "Inventory route linked:",
        INVENTORY_PATH in destinations
    )

    print("Raw navigation labels exported: 0")
    print("Private URLs exported: 0")


def deep_map_dashboard(page):

    print("OM AI PHASE 5 STARTED")

    inspect_navigation(page)
    inspect_inventory(page)

    print("Unknown business controls clicked: 0")
    print("Business records exported: 0")
    print("OM AI DEEP DISCOVERY COMPLETED")
