# OM AI deployment — step-by-step

## 0. Keep the existing system intact

Use **a new Apps Script project**. Never paste OM AI's `doGet()` into your existing OM Universal login gateway; that would conflict with your current dashboard.

## 1. Create the project

1. Open https://script.google.com/ and select **New project**. Name it `OM AI — Private Intelligence`.
2. In the editor, add script files `Config`, `Setup`, `Api`, `Analysis`, `Monitor`, `FuelSources`, `FuelImageImport`, and `AI`. For each one, paste the entire corresponding `.gs` file from `apps-script/`.
3. Add HTML files `Index`, `Styles`, and `Client`. Paste the entire contents of the respective `.html` files. These are **HTML** files, not `.gs` scripts.
4. In Project Settings enable **Show appsscript.json manifest file in editor**, then replace its content with `apps-script/appsscript.json`.
5. Save. The included manifest uses the New York timezone for Florida store reporting and declares required Sheets, UrlFetch, email, and trigger scopes.

## 2. Configure owner and private Sheets

1. In Apps Script → **Project Settings → Script Properties**, add `OWNER_EMAIL` with your actual Google sign-in email (do not use an example address).
2. From the function selector run **`setupOmAi()`** once under that account. Approve Google permissions. The first run creates **a separate private Google Sheet** named `OM AI — Private Intelligence Database`.
3. Open the execution log to copy the Sheet URL. You can also find its ID in Script Property `OM_AI_SHEET_ID`.
4. Open the `Stores` tab. Confirm Quick-C's address and **verify its latitude/longitude before using weather/traffic radius checks**. Enter actual addresses and coordinates for `INVERNESS` and `VAPESTORE` or leave them blank; a blank location disables geographic monitoring for that store.
5. In the `Users` tab, add only approved Google accounts. Allowed roles are `Admin`, `Manager`, and `Viewer`; `active` should read `Yes`. For a Manager/Viewer, comma-separate allowed store IDs, e.g. `QUICKC,INVERNESS`.
6. Share the new private OM AI Sheet only with trusted staff using the least Google Drive access needed. **Because this app runs as the person accessing it, it needs that person's permission to read the Sheet.** Editors are needed for record writes. **Sharing this one Sheet exposes every store's underlying tab records to that person, regardless of the app's store filter.** Do not give access to staff who must be prevented from seeing the other stores. Owner-only protections are applied to the Users, Stores and AuditLog tabs; verify these protections in Sheets.

**Important:** This is a separate database. It does not modify the original management sheet or automatically import your existing 2023–2026 sales history.

## 3. Deploy private web app

1. Click **Deploy → New deployment → Web app**.
2. Set **Execute as: User accessing the web app**.
3. Select the narrowest practical **Who has access** choice available for your staff (for cross-account businesses, Google may show `Anyone with Google account` or `Anyone`). Do not select `Execute as me` to work around missing Sheet access.
4. Copy the deployed `/exec` URL. Each user opens it with their approved Google account. The script checks both Google identity and the `Users` sheet.
5. Verify: Admin can see all assigned stores; Manager can see only permitted stores and create records; Viewer can read but not submit. An email not on the allowlist must be denied.

**Do not place Apps Script API keys or raw business data in the existing public GitHub Pages repo.** If you want a portal shortcut, add a simple link from your existing private menu to the OM AI `/exec` URL. The underlying dashboard still requires authentication.

## 4. Configure external sources

- **NWS:** No API key needed. NWS supports US locations via `api.weather.gov`. The code looks up the hourly forecast URL from `/points/{lat},{lon}`, then reads `/alerts/active?point=...`. It labels forecast weather rather than claiming a thermometer reading.
- **Traffic:** Obtain a developer key from https://developer.tomtom.com/. In Script Properties add `TOMTOM_API_KEY`. The code requests nearby road speed and incident information. Missing key or provider errors are shown as missing data, not “no traffic.” Review quota and pricing for your plan.
- **Road construction:** Use FL511 (https://fl511.com/) and FDOT project reports to verify and manually create roadwork events in OM Radar. No unsupported official FL511/FDOT scraper is included.
- **News:** Google News RSS searches are best effort, may be rate-limited, and must be confirmed against articles or official sources before action.
- **AI:** Obtain an API key through a supported Gemini developer project and put `GEMINI_API_KEY` in Script Properties. Optionally set `GEMINI_MODEL`, default `gemini-2.5-flash`. This endpoint/model may change with availability and quotas. The key is never sent to the browser. The assistant receives limited aggregate context, not raw employee/customer records.

Select **OM Radar → Refresh sources** to test each provider. Successful data appears in the Signals sheet. You may have to grant new script permissions on first use.

## 5. Schedule monitoring

Run `installOmAiHourlyMonitoring()` once as the owner in Apps Script. To add separate daily tasks for GasBuddy, AAA and MostEdge, also run `scheduledOmAiFuelTasks()` once (initial checklist) and `installOmAiFuelDailyTasks()` once (approximately 7 AM Eastern each day). These create review tasks, not automated unauthorized website scraping. See `FUEL-SOURCES.md`. This installs an hourly refresh trigger for the enabled stores. For a daily digest, set `DIGEST_EMAIL` in Script Properties and create a daily time-driven trigger for `scheduledOmAiDigest` (one email per Florida date). To disable monitoring run `removeOmAiHourlyMonitoring()`.

Monitor `Executions` for API failures or quota errors; Google Apps Script and provider rate limits apply. External availability is not guaranteed.

## 6. Enter records and import historical data

The buttons in the UI support daily sales, vendor audits, incidents, inventory items, tasks, external events, expenses, operating measurements and compliance deadlines. For legacy sales, clean the old Sheets into one row per store and date with the sample headers in `samples/normalized-sales.csv`, then run in the editor:

```javascript
importNormalizedSalesFromSheet('YOUR_CLEANED_SHEET_ID', 'NormalizedSales');
```

The importer is owner-only and skips dates already in the OM AI Sales tab. It intentionally refuses mixed-format tables instead of guessing which row is the correct sales observation.

## 7. Confirm before going live

- Check authorized vs unauthorized Google accounts.
- Test each form, task update and Viewer read-only behavior.
- Verify 3 store IDs and geographic coordinates.
- Verify vendor formula: `audit_total - (invoice_total - discount - credit)`.
- Enter a few verified sales days; inspect sales-chart and forecast statuses.
- Test NWS outage and TomTom missing-key behavior.
- Verify historical data before using any sales impact estimates.
- Enable Sheet version history/periodic backup and a retention policy.

## Common troubleshooting

- **Access denied:** Google email missing, unapproved in Users tab, or no Sheet sharing. Confirm deployment runs as *user accessing*.
- **No store data:** Blank Sheets are expected until entries/import. The system does not fabricate sales.
- **Traffic not configured:** Add TOMTOM_API_KEY in Script Properties, then refresh.
- **No forecast:** Need at least 14 records total and 3 comparable historical weekdays for a predicted date.
- **Gemini HTTP error:** Validate key/model/quotas; the rest of the app works without AI.
- **Multiple apps' `doGet()` conflict:** Use a separate Apps Script project as prescribed.
