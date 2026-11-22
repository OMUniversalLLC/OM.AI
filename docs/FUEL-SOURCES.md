# OM AI Fuel Sources — Source-by-source tasks and verified screenshots

## 1. Separate jobs for each website

| Source | Data role | Task | Do not assume |
| --- | --- | --- | --- |
| GasBuddy | Nearby competitor station prices | Record station/address, grade, cash/card, price, price-reported time, capture time and screenshot link | All posted prices are current, accurate or free for automated collection |
| AAA | Florida / Hillsborough county market averages | Record dated average price for Regular, Midgrade, Premium and Diesel | County average is the competitor station price |
| MostEdge | Private store fuel operational report | Enter an authorized exported daily report: opening/delivered/sold/closing gallons, retail and verified cost, report ID, screenshot/export link | Public website contains private report; scraping the logged-in account is permitted |

When you paste a screenshot into Google Sheets, preserve it on an Evidence tab or store in a restricted Drive folder and paste the HTTPS link into `evidence_url`. A picture alone is **not** structured numerical data: manually transcribe and verify. An optional **Extract screenshot draft** action uses your configured Gemini API key to read a PNG/JPEG/PDF stored in Google Drive. This sends the selected report to Gemini only after the user clicks that action. Results are review-only; nothing is saved automatically. Confirm every number before entering the store fuel report.

## 2. Install on the existing OM AI private database

1. Copy updated `Config.gs`, `Setup.gs`, `Api.gs`, `Client.html` and **new** `FuelSources.gs` into your **separate private OM AI Apps Script project**. Do not replace the existing public dashboard gateway.
2. Re-run `setupOmAi()` as owner. It will create four **new** private tabs: `FuelSources`, `FuelObservations`, `FuelReports`, `FuelSourceTasks`. Existing OM AI data remains intact as long as previous table headers have not been changed.
3. In Apps Script, run `scheduledOmAiFuelTasks()` once to generate today's checklists, and `installOmAiFuelDailyTasks()` to schedule creation of one task per website per store daily around 7 AM Eastern. Time-based Apps Script triggers do not guarantee exact minute execution.
4. Open the deployed private OM AI web app, select store, then **Fuel Sources**. Use **Add reference price** for AAA/GasBuddy, and **Add store fuel report** for MostEdge data. `Completed` source tasks require an HTTPS link to source evidence.
5. Imported rows can be audited in the private Sheets. For strict permissions across multiple stores, **do not share** the underlying database Sheet with users who must be restricted to one store: a shared Sheet bypasses per-store UI restrictions.

## 3. Spreadsheet template

`OM-AI-Fuel-Source-Monitor.xlsx` is a separate starter template designed to be imported into Google Sheets. It contains `START HERE`, `Fuel Daily Report`, `Reference Prices`, `Source Tasks`, `Source Directory`, `Evidence Log`, and `News Impact`. Those names are optimized for human copy/paste and not interchangeable with database tab schemas. If you need to import existing rows into the private database, map the human-readable columns first and review the data.

## 4. Calculations

- Expected closing gallons = opening gallons + delivered gallons − sold gallons.
- Variance gallons = actual closing gallons − expected closing gallons.
- Cash margin per gallon = cash retail − replacement cost (before taxes, fees and other costs).
- Price difference to AAA = cash retail − captured *same-day, same-grade* AAA average.
- Price difference to GasBuddy = cash retail − captured *same-day, same-grade* lowest recorded nearby cash price; verify posted time and station comparability.

Do not auto-change pump prices or imply an automatic cause-and-effect relationship from an article. More reliable forecasting requires supplier invoices, actual POS/fuel data, nearby posted prices and dated historical observations.

## 5. Live surveillance and smart-speaker alerts

CCTV monitoring is **not** included or activated in this fuel update. It requires on-premises camera/NVR access, a verified person/zone detector or trained operator, documented camera/voice policy, and a configured speaker (such as a Home Assistant-compatible endpoint). Keep footage local wherever possible. A cautious trigger can require a customer-zone occupancy of 20–30 seconds, no employee in the assigned counter zone, confirmation from a second frame, and an alert cooldown. Avoid face identification or inference about customer identity. Failure of a camera, network or detector must show `unavailable`, not `counter clear`.

## 6. Provider access limits

The default integration **does not scrape** websites or private account data, does not use third-party credentials and does not silently post competitor prices. Add approved APIs or CSV exports only after permission and data licensing are confirmed. Hourly NWS/TomTom source monitoring is separate from the daily manual fuel-price task creation.
