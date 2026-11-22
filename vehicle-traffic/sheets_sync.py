"""Publish the current dashboard metrics to a designated Google Sheet."""
from datetime import datetime, timezone
import json
import os


def values(status):
    counts = status["observed_crossings"]
    cameras = status["cameras"]
    fuel = status["fuel"] or {}
    people = status["people_now"]
    directions = (counts["road_negative_to_positive"], counts["road_positive_to_negative"])
    road_seen = cameras["road"] == "observing" or any(directions)
    highway = counts["fuel_road_negative_to_positive"] + counts["fuel_road_positive_to_negative"]
    return [[value if value is not None else ""] for value in (
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        status["florida_date"], cameras["road"], cameras["fuel"], cameras["door"],
        sum(directions) if road_seen else None,
        directions[0] if road_seen else None, directions[1] if road_seen else None,
        counts["entered"] if cameras["driveway"] == "observing" or counts["entered"] else None,
        counts["exited"] if cameras["driveway"] == "observing" or counts["exited"] else None,
        highway if status["fuel_road_counting"] and (cameras["fuel_road"] == "observing" or highway) else None,
        fuel.get("at_pumps"), fuel.get("waiting"), fuel.get("queue_moving"), fuel.get("bypass_zone"),
        people["road"], people["fuel"], people["door"],
        counts["door_entered"] if status["door_counting"] and (cameras["door"] == "observing" or counts["door_entered"]) else None,
        counts["door_exited"] if status["door_counting"] and (cameras["door"] == "observing" or counts["door_exited"]) else None,
    )]


def connect():
    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2 import service_account

    info = json.loads(os.environ["OM_TRAFFIC_SHEETS_KEY"])
    if info.get("type") != "service_account" or info.get("token_uri") != "https://oauth2.googleapis.com/token":
        raise ValueError("Expected a Google-issued service account key.")
    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/spreadsheets"])
    return AuthorizedSession(credentials, refresh_timeout=10)


def sync(reports, stop, spreadsheet):
    import re

    if not re.fullmatch(r"[A-Za-z0-9_-]+", spreadsheet):
        reports.set_sheet_status("error", "Spreadsheet ID is invalid.")
        return
    endpoint = (f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet}"
                "/values/%27Live%20Traffic%27%21B2%3AB21")
    try:
        session = connect()
    except (ImportError, ValueError, KeyError):
        reports.set_sheet_status("error", "Google Sheets setup is incomplete. Run Configure Google Sheets.")
        return
    with session:
        while not stop.is_set():
            try:
                response = session.put(endpoint, params={"valueInputOption": "RAW"},
                                       json={"values": values(reports.current())}, timeout=10)
                if response.ok:
                    reports.set_sheet_status("synced", datetime.now(timezone.utc).isoformat(timespec="seconds"))
                else:
                    reports.set_sheet_status("error", f"Google Sheets returned HTTP {response.status_code}.")
            except Exception:
                reports.set_sheet_status("error", "Google Sheets sync failed. It will retry automatically.")
            stop.wait(60)
