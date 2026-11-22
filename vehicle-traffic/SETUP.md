# OM AI Vehicle Traffic

Windows monitor for road and driveway traffic, fuel-pump activity, and people detected in camera previews. The browser dashboard shows current counts and stores daily crossing totals on the PC.

## Start on Windows

1. Use Python 3.12. Run these commands from this directory.

```powershell
py -3.12 -m venv .venv
$python = '.\.venv\Scripts\python.exe'
& $python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
& $python -m pip install opencv-python tzdata
Copy-Item .\site.example.json .\site.json
```

2. Edit the local `site.json` with the recorder IP address or hostname. The launcher expects RTSP on port 554 with channels 1 (road and driveway), 6 (pumps and optional highway line), and 3 (storefront).
3. Run `& '.\Auto Setup OM AI.cmd'` and enter your recorder viewer login when prompted. On a fresh checkout, draw the lines and zones in the calibration window. Use **S** to skip optional areas. Auto Setup reuses and verifies a saved calibration or a locally supplied `calibration-preset.json`.
4. Open [the local dashboard](http://127.0.0.1:8765/). Run `Install Desktop Shortcut.cmd` to add a Windows desktop launcher. Run `& '.\Auto Setup OM AI.cmd' -ChangeLogin` if the recorder login changes.

### Calibration

| Camera | Markings |
| --- | --- |
| 1 | Draw a line across the visible travel lanes and a second line across the driveway mouth. Mark the lot side of the driveway line. |
| 6 | Outline the pump area. The queue, bypass lane, and separate highway line are optional. |
| 3 | Mark a doorway line if the crossing is visible. People detection also works without a doorway line. |

Compare the dashboard with actual crossings after installation. The two road counters cover independent camera views.

## Google Sheets

Enter the target spreadsheet ID in the local `site.json`. Name the destination tab **Live Traffic**. Import `live-traffic-template.csv` starting at A1 if you are creating a fresh tab. Enable the Sheets API, share the spreadsheet with your Google service account as Editor, and run `Configure Google Sheets.cmd` to load its key on the PC. Restart the monitor. It updates B2:B21 about once a minute with counts and status.

## Private web access

Use Tailscale Serve on an authorized private network to open the same dashboard from another device. With the monitor running and HTTPS enabled for your network, run `tailscale serve --bg 8765` on the Windows PC. Open the HTTPS address printed by the command.

## Local files

Recorder and Sheets credentials are saved for the current Windows account. Keep credentials, site configuration, calibration, count history, and camera media outside version control. The included ignore rules cover the standard runtime paths.
