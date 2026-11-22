# OM AI data dictionary and business formulas

A private Google Sheet is created on first setup. Table headers are defined in `Config.gs` and should not be renamed without a schema migration.

| Tab | Main fields | Why it matters |
| --- | --- | --- |
| Users | email, role, store_ids, active | Enforces access |
| Stores | store_id, address, coordinates, timezone | Geographic data routing |
| Sales | date, inside_sales, customers, transactions, fuel_gallons, fuel_sales, lottery_sales, car_wash_sales | Trends, volumes, forecasts |
| Inventory | sku, item_name, department, on_hand, reorder_point, unit_cost, retail_price | Low-stock alerts |
| Vendors | invoice_total, audit_total, discount, credit, status | Financial reconciliation |
| Expenses | date, category, vendor, amount, payment_method | Expense reporting |
| Operations | area, metric, value, unit | ATM, lottery, car wash, fuel, power, equipment indicators |
| Compliance | name, category, due_date, owner, status | Renewal alerts |
| Tasks | title, assigned_to, due_date, priority, status | Work management |
| Incidents | date, category, severity, description, status | Safety and operations log |
| ExternalEvents | title, category, source_url, start_date, end_date, status | Verified construction, events, external impacts |
| Signals | source, kind, observed_at, value, details, source_key, expires_at | Fetched weather/traffic/news observations |
| AuditLog | actor, action, store_id, record_id | Internal accountability |

## Metric definitions

- **Inside sales:** Store sales excluding fuel and lottery; match this to your POS definition before import.
- **Customer count:** The store's recorded customer count; may differ from transactions depending on POS/report definitions.
- **Average ticket:** Inside sales / transactions (only when transactions >0).
- **Vendor net expected:** `invoice_total − discount − credit`.
- **Vendor variance:** `audit_total − net_expected` (positive means audit exceeds expected; negative means audit is below expected). Investigate even when discounts have not been entered.
- **Low stock:** `on_hand <= reorder_point`.
- **7-day sales change:** Compare average of latest seven *recorded* dates against the prior seven. Missing days can distort the result; do not treat as continuous calendar weeks unless daily coverage is complete.
- **Forecast baseline:** Most recent eight matching weekdays, with linear recency weights. Requires at least 14 total historical dates and three matching weekdays. The displayed range is heuristic (15% to 50%), not a calibrated confidence interval.
- **Expenses last 7 days:** Recorded expense amounts whose date falls in the most recent seven days. Not net profit; purchase cost, payroll and tax coverage must be validated.

## Historical sales import

One row should represent **one store on one calendar date**. The required headers for `importNormalizedSalesFromSheet` are `date`, `store_id`, `inside_sales`, `customers`. Optional columns: `transactions`, `fuel_gallons`, `fuel_sales`, `lottery_sales`, `car_wash_sales`, `notes`.

Before importing mixed legacy Sheets from 2023–2026, map each historical source to the canonical headers, extract dates explicitly, verify daily vs month-to-date vs prior-year comparison fields, and reconcile several sample dates against the original reports. This MVP does not automate that legacy cleanup.

## Suggested extensions

Use the `Operations` tab for generic metrics (ATM withdrawals, fees, car wash count, lottery ticket activation, fuel tank levels, pump downtime). Dedicated automated equipment feeds, payroll integration, refrigeration monitoring, camera intelligence, FDOT project databases, and bank reconciliation require additional connectors and security controls.
