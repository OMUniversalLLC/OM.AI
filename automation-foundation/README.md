# Automation foundation (staging only)

This directory contains a manual, synthetic-data browser smoke test. It does not access any private website, upload data, or change the live dashboard.

Production plan: run authorized read-only Playwright extractors on a private runner/repository, validate records in Python, send authenticated batches to an Apps Script endpoint, store them in restricted Google Sheets, and use a server-authorized dashboard data endpoint. ChatGPT Tasks can review available records and report discrepancies.

Before enabling schedules: create a private repository, confirm source access and permissions, configure private destinations, test extraction against known totals, implement idempotent writes and server-side authorization, and confirm budget. Never commit credentials, browser storage state, screenshots of private reports, or business records. Do not publish private spreadsheet data through GitHub Pages.

Local test: install requirements, run playwright install chromium, then python smoke_test.py.
