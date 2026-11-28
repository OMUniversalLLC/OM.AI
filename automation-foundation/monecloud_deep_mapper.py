import re
from urllib.parse import urlsplit

from monecloud_mapper import MODULES

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


def inventory_structure_diagnostics(page):

    import time

    print("================================")
    print("OM AI PHASE 6B STRUCTURE DIAGNOSTICS")
    print("================================")

    script = r"""
        () => {
            const visible = e =>
                e.getClientRects().length > 0 &&
                getComputedStyle(e).visibility !== "hidden";

            const norm = s =>
                (s || "").toLowerCase()
                    .replace(/\s+/g, " ").trim();

            const result = {
                tables: [],
                selectCount: 0,
                locationControls: 0,
                placeholderSelections: 0,
                textInputs: 0,
                gridRows: 0,
                busyIndicators: 0,
                emptyMessages: 0
            };

            const tables =
                Array.from(document.querySelectorAll("table"));

            for (let i = 0; i < tables.length; i++) {

                const table = tables[i];

                const headerRows = table.tHead
                    ? Array.from(table.tHead.rows)
                    : [];

                const bodyRows =
                    Array.from(table.tBodies)
                    .flatMap(b => Array.from(b.rows));

                const headerWidths = [];

                let inventoryHeader = false;
                let compatibleRows = 0;

                for (const header of headerRows) {

                    const cells = Array.from(header.cells);

                    headerWidths.push(cells.length);

                    const labels = cells.map(
                        c => norm(c.innerText)
                    );

                    const hasUPC = labels.some(
                        x => /\b(upc|barcode)\b/.test(x)
                    );

                    const hasName = labels.some(
                        x => /\b(item name|product name|description)\b/.test(x)
                    );

                    const hasPrice = labels.some(
                        x => /\b(price|retail)\b/.test(x)
                    );

                    if (hasUPC && hasName && hasPrice) {

                        inventoryHeader = true;

                        if (cells.every(c =>
                            c.colSpan === 1 &&
                            c.rowSpan === 1
                        )) {

                            compatibleRows = bodyRows.filter(
                                row =>
                                    visible(row) &&
                                    row.cells.length === cells.length &&
                                    Array.from(row.cells).every(
                                        c => c.colSpan === 1
                                    )
                            ).length;
                        }
                    }
                }

                const widths = {};

                for (const row of bodyRows) {

                    const count = row.cells.length;

                    widths[count] =
                        (widths[count] || 0) + 1;
                }

                result.tables.push({
                    number: i + 1,
                    visible: visible(table),
                    headerRows: headerRows.length,
                    headerWidths: headerWidths,
                    bodyRows: bodyRows.length,
                    visibleBodyRows: bodyRows.filter(visible).length,
                    bodyWidths: widths,
                    inputCells: table.querySelectorAll(
                        "tbody td input"
                    ).length,
                    inventoryHeader: inventoryHeader,
                    compatibleRows: compatibleRows
                });
            }

            const selects = Array.from(
                document.querySelectorAll("select")
            ).filter(visible);

            result.selectCount = selects.length;

            for (const select of selects) {

                const label = norm(
                    [
                        select.name,
                        select.id,
                        select.getAttribute("aria-label"),
                        ...Array.from(select.labels || [])
                            .map(x => x.innerText)
                    ].filter(Boolean).join(" ")
                );

                if (/\b(location|store|site)\b/.test(label)) {
                    result.locationControls++;
                }

                const option =
                    select.selectedOptions[0];

                if (
                    !option ||
                    !option.value ||
                    /^(select|choose|please select)(\b|$)/
                        .test(norm(option.textContent))
                ) {
                    result.placeholderSelections++;
                }
            }

            result.textInputs = Array.from(
                document.querySelectorAll(
                    'input[type="text"], input[type="search"]'
                )
            ).filter(visible).length;

            result.gridRows = Array.from(
                document.querySelectorAll(
                    '[role="row"]'
                )
            ).filter(visible).length;

            result.busyIndicators = Array.from(
                document.querySelectorAll(
                    '[aria-busy="true"], [role="progressbar"]'
                )
            ).filter(visible).length;

            result.emptyMessages = Array.from(
                document.querySelectorAll(
                    'td, [role="status"], [role="alert"]'
                )
            ).filter(e =>
                visible(e) &&
                /^(no data|no records|no results|no items|no matching records)/i
                    .test((e.innerText || "").trim())
            ).length;

            return result;
        }
    """

    deadline = time.monotonic() + 45

    while True:

        if page.is_closed() or not trusted(page, INVENTORY_PATH):
            raise RuntimeError("Inventory destination changed")

        result = page.evaluate(script)

        ready = any(
            table["inventoryHeader"]
            and table["compatibleRows"] > 0
            for table in result["tables"]
        )

        if ready or time.monotonic() >= deadline:
            break

        page.wait_for_timeout(3000)

    print("Inventory loading readiness:", ready)

    print("Total HTML tables:", len(result["tables"]))

    for table in result["tables"]:

        print(
            "TABLE", table["number"],
            "| visible:", table["visible"],
            "| header rows:", table["headerRows"],
            "| header widths:", table["headerWidths"],
            "| body rows:", table["bodyRows"],
            "| visible body rows:", table["visibleBodyRows"],
            "| body widths:", table["bodyWidths"],
            "| input cells:", table["inputCells"],
            "| inventory header:", table["inventoryHeader"],
            "| compatible rows:", table["compatibleRows"]
        )

    print("Visible select controls:", result["selectCount"])
    print("Location controls:", result["locationControls"])
    print("Placeholder selections:", result["placeholderSelections"])
    print("Text input controls:", result["textInputs"])
    print("ARIA grid rows:", result["gridRows"])
    print("Busy indicators:", result["busyIndicators"])
    print("Empty-state messages:", result["emptyMessages"])

    print("Private product values exported: 0")
    print("OM AI PHASE 6B DIAGNOSTICS COMPLETED")
    print("================================")


def validate_inventory_rows(page):
    inventory_structure_diagnostics(page)


    print("================================")
    print("OM AI PHASE 6 ROW VALIDATION")
    print("================================")

    if not trusted(page, INVENTORY_PATH):
        raise RuntimeError("Unexpected inventory destination")

    result = page.evaluate("""
        () => {
            const normalize = value =>
                (value || "").toLowerCase()
                    .replace(/\\s+/g, " ").trim();

            const visible = element =>
                element.getClientRects().length > 0
                && getComputedStyle(element).visibility
                    !== "hidden";

            const candidates = [];

            for (const table of document.querySelectorAll("table")) {

                if (!visible(table) || !table.tHead) {
                    continue;
                }

                for (const headerRow of table.tHead.rows) {

                    const cells = Array.from(headerRow.cells);

                    if (
                        cells.some(c =>
                            c.colSpan !== 1 || c.rowSpan !== 1
                        )
                    ) {
                        continue;
                    }

                    const headers = cells.map(c =>
                        normalize(c.innerText)
                    );

                    const upc = headers.findIndex(h =>
                        /\\b(upc|barcode)\\b/.test(h)
                    );

                    const name = headers.findIndex(h =>
                        /^(item name|product name|description|item description)$/.test(h)
                    );

                    const price = headers.findIndex(h =>
                        /^(price|retail|retail price|selling price)$/.test(h)
                    );

                    if (
                        upc < 0 ||
                        name < 0 ||
                        price < 0
                    ) {
                        continue;
                    }

                    const rows = Array.from(table.tBodies)
                        .flatMap(body => Array.from(body.rows))
                        .filter(row =>
                            visible(row)
                            && row.cells.length === headers.length
                            && Array.from(row.cells).every(
                                c => c.colSpan === 1
                            )
                        );

                    candidates.push({
                        rows,
                        upc,
                        name,
                        price
                    });

                    break;
                }
            }

            const populated = candidates.filter(
                item => item.rows.length > 0
            );

            const output = {
                matchingTables: candidates.length,
                populatedTables: populated.length,
                sampledRows: 0,
                validUPC: 0,
                validName: 0,
                validPrice: 0,
                validRows: 0,
                duplicateUPC: 0
            };

            if (populated.length !== 1) {
                return output;
            }

            const target = populated[0];
            const seen = new Set();

            for (const row of target.rows.slice(0, 50)) {

                output.sampledRows++;

                const upc =
                    row.cells[target.upc].innerText.trim();

                const name =
                    row.cells[target.name].innerText.trim();

                const price =
                    row.cells[target.price].innerText
                        .replace(/[$,]/g, "").trim();

                const upcOK =
                    /^(\\d{8}|\\d{12}|\\d{13}|\\d{14})$/
                        .test(upc);

                const nameOK = name.length > 0;

                const priceOK =
                    /^\\d+(\\.\\d{1,2})?$/.test(price)
                    && Number.isFinite(Number(price));

                if (upcOK) {
                    output.validUPC++;

                    if (seen.has(upc)) {
                        output.duplicateUPC++;
                    }

                    seen.add(upc);
                }

                if (nameOK) {
                    output.validName++;
                }

                if (priceOK) {
                    output.validPrice++;
                }

                if (upcOK && nameOK && priceOK) {
                    output.validRows++;
                }
            }

            return output;
        }
    """)

    print("Matching inventory tables:",
          result["matchingTables"])

    print("Populated inventory tables:",
          result["populatedTables"])

    print("Rows sampled:", result["sampledRows"])
    print("Valid UPC format:", result["validUPC"])
    print("Valid product names:", result["validName"])
    print("Valid retail prices:", result["validPrice"])
    print("Complete valid rows:", result["validRows"])
    print("Repeated UPC occurrences:", result["duplicateUPC"])

    print("Raw product records exported: 0")

    if (
        result["populatedTables"] != 1
        or result["sampledRows"] == 0
        or result["validRows"] == 0
    ):
        print("PHASE 6 ROW VALIDATION: INCONCLUSIVE")
        raise RuntimeError("Inventory rows require further mapping")

    if result["validRows"] == result["sampledRows"]:
        print("PHASE 6 ROW VALIDATION: PASSED")
    else:
        print("PHASE 6 ROW VALIDATION: PARTIAL")
        raise RuntimeError("Some inventory rows failed validation")


def inspect_inventory(dashboard):

    print("================================")
    print("INVENTORY PAGE STRUCTURE TEST")
    print("================================")

    page = dashboard.context.new_page()

    try:

        response = page.goto(
            "https://" + HOST + INVENTORY_PATH,
            wait_until="domcontentloaded",
            timeout=60000
        )

        if response is None:
            raise RuntimeError("No inventory page response")

        print("Inventory HTTP status:", response.status)

        if response.status >= 400:
            raise RuntimeError("Inventory page unavailable")

        page.wait_for_timeout(8000)

        if not trusted(page, INVENTORY_PATH):
            raise RuntimeError("Inventory destination changed")

        if page.locator(
            "input[type=password]:visible"
        ).count():
            raise RuntimeError("Authentication required")

        tables = page.locator(
            'table:visible, '
            '[role="grid"]:visible, '
            '[role="table"]:visible'
        )

        headers = page.locator(
            'thead th:visible, '
            '[role="columnheader"]:visible'
        ).all_text_contents()

        detected_headers = []

        for field, aliases in SAFE_HEADERS.items():

            if any(
                matches(header, aliases)
                for header in headers
            ):
                detected_headers.append(field)

        print("Inventory route reached: YES")
        print("Visible tables or grids:", tables.count())
        print("Visible column headers:", len(headers))

        print("Detected inventory schema:")

        for field in SAFE_HEADERS:

            status = (
                "DETECTED"
                if field in detected_headers
                else "NOT YET DETECTED"
            )

            print(f"{field}: {status}")

        print(
            "Date input controls:",
            page.locator('input[type=date]:visible').count()
        )

        print(
            "Dropdown controls:",
            page.locator(
                'select:visible, [role="combobox"]:visible'
            ).count()
        )

        print(
            "Search controls:",
            page.locator(
                'input[type=search]:visible'
            ).count()
        )

        controls = navigation_inventory(page)

        for label, aliases in {
            "Export": ["export", "download", "excel", "csv"],
            "Search": ["search", "filter"],
            "Pagination": ["next", "previous"],
            "Print": ["print"],
        }.items():

            count = sum(
                item["visible"]
                and matches(item["label"], aliases)
                for item in controls
            )

            print(f"{label} control candidates:", count)

        if tables.count() > 0 and len(detected_headers) >= 2:
            print("Inventory schema verification: PASSED")
            validate_inventory_rows(page)
        else:
            print("Inventory schema verification: INCONCLUSIVE")

    finally:
        page.close()


def deep_map_dashboard(page):

    print("OM AI PHASE 5 STARTED")

    inspect_navigation(page)
    inspect_inventory(page)

    print("Business controls clicked: 0")
    print("Business records exported: 0")
    print("OM AI PHASE 5 DISCOVERY COMPLETED")
