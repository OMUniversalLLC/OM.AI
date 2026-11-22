# OM AI source workspace

- `apps/operations-dashboard` contains the React operations reporting dashboard and its Pages build.
- `preview/dashboard-export/index.html` is a standalone, sample-data website.
- `vehicle-traffic` contains the Windows monitor, calibration tools, browser dashboard, and Sheets publisher.
- `apps-script`, `surveillance`, `edge-agent`, `network-agent`, and `pc-agent` contain the deployment components.

## Run the operations dashboard locally

```bash
cd apps/operations-dashboard
pnpm install
pnpm run dev:pages
```

## Set up a private deployment

Use approved local or private services for the operational dashboard and integrations. Review [deployment guidance](docs/UNIFIED-SECURITY-AND-DEPLOYMENT.md) before enabling real data. Store the site profile, camera inventory, and account credentials in restricted storage. For local surveillance, the agent loads `surveillance/cameras.local.json` if present. Apps Script owners can configure `OM_PRIVATE_CAMERA_PLAN` as a private Script Property for seeding or explicitly aligning camera names.
