"""Run OM AI traffic monitoring on the store PC."""
import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from math import dist
import os
from pathlib import Path
from threading import Event, Lock, Thread
import time
from urllib.parse import urlsplit
import webbrowser
from zoneinfo import ZoneInfo

from counting import Counter

VEHICLE_ROLES = ("road", "driveway", "fuel")
ROLES = (*VEHICLE_ROLES, "door", "fuel_road")
CAMERA_ROLES = ("road", "fuel", "door")
EVENTS = ("road_negative_to_positive", "road_positive_to_negative", "entered", "exited",
          "door_entered", "door_exited",
          "fuel_road_negative_to_positive", "fuel_road_positive_to_negative")


def camera_settings(config):
    if not set(VEHICLE_ROLES) <= config.keys() or not config.keys() <= set(ROLES):
        raise ValueError("Calibrate the road, driveway and fuel views.")

    def points(value, minimum):
        return (isinstance(value,list) and len(value) >= minimum and
                all(isinstance(point,list) and len(point)==2 and
                    all(type(n) in (int,float) and 0<=n<=1 for n in point) for point in value))

    streams = {}
    for role, spec in config.items():
        if spec.get("confirmed") is not True:
            raise ValueError(f"Verify the camera view and calibration for {role} first.")
        url = stream_url(role)
        if urlsplit(url).scheme not in {"rtsp","rtsps"} or not urlsplit(url).hostname:
            raise ValueError(f"Missing a valid local RTSP address for {role}.")
        streams[role] = url
        if role == "fuel":
            for name in ("queue","at_pumps","bypass_zone"):
                zone = spec.get(name,[])
                if name in ("queue", "bypass_zone") and not zone:
                    continue
                if not points(zone,3):
                    raise ValueError(f"Calibrate the {name} polygon.")
                area = sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(zone,zone[1:]+zone[:1]))
                if abs(area) < .0001:
                    raise ValueError(f"The {name} polygon must have an area.")
            if not 1 <= spec.get("wait_seconds",0) <= 180 or not .001 <= spec.get("motion_radius",0) <= .1:
                raise ValueError("Provide a fuel wait threshold and movement tolerance.")
        elif not points(spec.get("line"),2) or len(spec["line"])!=2 or dist(*spec["line"])<.02:
            raise ValueError(f"Calibrate two distinct line endpoints for {role}.")
        if role in ("driveway", "door") and spec.get("inside_side") not in (-1, 1):
            raise ValueError(f"Set the inside side for {role}.")
    if stream_url("door") and "door" not in streams:
        streams["door"] = stream_url("door")
    for role, url in streams.items():
        sharing = {key for key, value in streams.items() if value == url}
        if len(sharing) > 1 and sharing not in ({"road", "driveway"}, {"fuel", "fuel_road"}):
            raise ValueError("Only related counting views may share a camera stream.")
    return streams


def stream_url(role):
    if role == "fuel_road":
        return stream_url("fuel")
    url = os.environ.get(f"OM_VEHICLE_{role.upper()}_RTSP", "")
    return url or (stream_url("road") if role == "driveway" else "")


class Stream:
    def __init__(self, cv, url, stop):
        self.lock = Lock()
        self.latest = None
        self.session = 0
        self.worker = Thread(target=self.receive,args=(cv,url,stop),daemon=True)

    def receive(self, cv, url, stop):
        while not stop.is_set():
            capture = cv.VideoCapture(url,cv.CAP_FFMPEG,[
                cv.CAP_PROP_OPEN_TIMEOUT_MSEC,4000,cv.CAP_PROP_READ_TIMEOUT_MSEC,3000])
            self.session += 1
            try:
                while capture.isOpened() and not stop.is_set():
                    ok, frame = capture.read()
                    if not ok:
                        break
                    with self.lock:
                        self.latest = (time.monotonic(),self.session,frame)
            finally:
                capture.release()
                with self.lock:
                    self.latest = None
            stop.wait(3)

    def read(self):
        with self.lock:
            return self.latest


class Detector:
    def __init__(self, cv):
        import torch
        from torchvision.models.detection import SSDLite320_MobileNet_V3_Large_Weights
        from torchvision.models.detection import ssdlite320_mobilenet_v3_large
        weights = SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
        self.cv, self.torch = cv, torch
        torch.set_num_threads(2)
        self.transform = weights.transforms()
        self.labels = {i: ("people" if name == "person" else "vehicles")
                       for i, name in enumerate(weights.meta["categories"])
                       if name in {"person", "car", "motorcycle", "bus", "truck"}}
        self.model = ssdlite320_mobilenet_v3_large(weights=weights).eval()

    def points(self, frame):
        h,w = frame.shape[:2]
        image = self.cv.cvtColor(frame,self.cv.COLOR_BGR2RGB)
        tensor = self.transform(self.torch.from_numpy(image).permute(2,0,1))
        with self.torch.inference_mode():
            output = self.model([tensor])[0]
        points = {"people": [], "vehicles": []}
        for (left, _, right, bottom), label, score in zip(
                output["boxes"].tolist(), output["labels"].tolist(), output["scores"].tolist()):
            if label in self.labels and score >= .5:
                points[self.labels[label]].append((min(1., max(0., (left + right) / (2 * w))),
                                                   min(1., max(0., bottom / h))))
        return points


class Reports:
    def __init__(self, path):
        self.timezone = ZoneInfo("America/New_York")
        self.path = path
        self.lock = Lock()
        self.totals = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.frames = {}
        self.previews = {}
        self.fuel = None
        self.door_counting = False
        self.fuel_road_counting = False
        self.people = {}
        self.sheet_sync = {"state": "disabled", "detail": None, "last_success": None}

    def set_sheet_status(self, state, detail):
        with self.lock:
            self.sheet_sync.update(state=state, detail=detail)
            if state == "synced":
                self.sheet_sync["last_success"] = detail

    def preview(self, role, stamp, jpeg):
        with self.lock:
            if jpeg is not None:
                self.previews[role] = stamp, jpeg

    def get_preview(self, role):
        with self.lock:
            stamp, jpeg = self.previews.get(role, (float("-inf"), None))
            return jpeg if time.monotonic() - stamp <= 4 else None

    def history(self):
        with self.lock:
            return {date: dict(counts) for date, counts in self.totals.items()}

    def update(self,role,events,occupancy,stamp,people=None):
        with self.lock:
            self.frames[role] = stamp
            if role in CAMERA_ROLES:
                self.people[role] = people
            if role == "fuel":
                self.fuel = occupancy
            if events:
                date = datetime.now(self.timezone).date().isoformat()
                day = self.totals.setdefault(date,{})
                for name in events:
                    day[name] = day.get(name,0)+1
                temporary = self.path.with_suffix(".tmp")
                temporary.write_text(json.dumps(self.totals),encoding="utf-8")
                temporary.replace(self.path)

    def current(self):
        with self.lock:
            date = datetime.now(self.timezone).date().isoformat()
            status = {role:"observing" if time.monotonic()-self.frames.get(role,float("-inf"))<=4
                      else "unavailable" for role in ROLES}
            totals = self.totals.get(date,{})
            return {"florida_date":date,"cameras":status,"observed_crossings":
                    {key:totals.get(key,0) for key in EVENTS},
                    "fuel":self.fuel if status["fuel"]=="observing" else None,
                    "door_counting": self.door_counting,
                    "fuel_road_counting": self.fuel_road_counting,
                    "sheet_sync": dict(self.sheet_sync),
                    "people_now": {role: self.people.get(role) if status[role] == "observing" else None
                                   for role in CAMERA_ROLES}}


def dashboard(reports, port):
    page = Path(__file__).with_name("dashboard.html").read_bytes()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                content, kind = page, "text/html; charset=utf-8"
            elif self.path == "/status.json":
                content = json.dumps(reports.current()).encode()
                kind = "application/json"
            elif self.path == "/history.json":
                content, kind = json.dumps(reports.history()).encode(), "application/json"
            elif urlsplit(self.path).path.startswith("/preview/"):
                camera = urlsplit(self.path).path.removeprefix("/preview/")
                content, kind = reports.get_preview(camera), "image/jpeg"
                if content is None:
                    return self.send_error(503)
            else:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type",kind)
            self.send_header("Cache-Control","no-store")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, *_):
            pass

    return ThreadingHTTPServer(("127.0.0.1",port),Handler)


def preview_image(cv, frame, points, roles, config):
    from calibration import draw_geometry, pixel

    height, width = frame.shape[:2]
    preview = cv.resize(frame, (min(width, 720), round(height * min(width, 720) / width)))
    for role in roles:
        draw_geometry(cv, preview, role, config.get(role, {}))
    for kind, color in (("vehicles", (100, 255, 100)), ("people", (255, 170, 255))):
        for point in points[kind]:
            cv.circle(preview, pixel(preview, point), 4, color, -1, cv.LINE_AA)
    ok, encoded = cv.imencode(".jpg", preview, [cv.IMWRITE_JPEG_QUALITY, 82])
    return encoded.tobytes() if ok else None


def monitor(cv, detector, config, urls, reports, fps, stop):
    roles_by_url = {}
    for role, url in urls.items():
        roles_by_url.setdefault(url, []).append(role)
    readers = {url: Stream(cv, url, stop) for url in roles_by_url}
    counters = {role: Counter(role, config[role]) for role in config}
    previous = {url: (0, None) for url in readers}
    last_preview = {url: 0 for url in readers}
    for reader in readers.values():
        reader.worker.start()
    while not stop.is_set():
        for url, reader in readers.items():
            sample = reader.read()
            if sample is None:
                continue
            stamp, session, frame = sample
            last, last_session = previous[url]
            if stamp - last < 1 / fps or time.monotonic() - stamp > 2:
                continue
            roles = roles_by_url[url]
            previous[url] = stamp, session
            points = detector.points(frame)
            people = len(points["people"])
            for role in roles:
                if role not in counters:
                    reports.update(role, [], None, stamp, people)
                    continue
                if session != last_session or stamp - last > 1.2:
                    counters[role].clear()
                events, occupancy = counters[role].step(
                    stamp, points["people" if role == "door" else "vehicles"])
                if occupancy is not None:
                    for zone, fields in (("queue", ("waiting", "queue_moving")),
                                         ("bypass_zone", ("bypass_zone",))):
                        if not config["fuel"].get(zone):
                            occupancy.update(dict.fromkeys(fields))
                reports.update(role, events, occupancy, stamp, people)
            if stamp - last_preview[url] >= .65:
                jpeg = preview_image(cv, frame, points, roles, config)
                for role in roles:
                    reports.preview(role, stamp, jpeg)
                last_preview[url] = stamp
        stop.wait(.015)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("calibration",type=Path)
    parser.add_argument("--port",type=int,default=8765)
    parser.add_argument("--fps",type=float,default=4,help="Target analyzed FPS per camera")
    parser.add_argument("--data",type=Path,default=Path("private/vehicle-counts.json"))
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.fps <= 10:
        parser.error("Analyzed FPS must be between 1 and 10.")
    config = json.loads(args.calibration.read_text(encoding="utf-8-sig"))
    urls = camera_settings(config)
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    import cv2
    args.data.parent.mkdir(parents=True,exist_ok=True)
    reports = Reports(args.data)
    reports.door_counting = "door" in config
    reports.fuel_road_counting = "fuel_road" in config
    server = dashboard(reports,args.port)
    Thread(target=server.serve_forever,daemon=True).start()
    stop = Event()
    print(f"Open http://127.0.0.1:{args.port} on the store PC. Press Ctrl+C to stop.")
    try:
        if args.open_browser:
            webbrowser.open(f"http://127.0.0.1:{args.port}/")
        print("Loading the AI model. A first run may download its weights.")
        detector = Detector(cv2)
        spreadsheet = os.environ.get("OM_TRAFFIC_SPREADSHEET_ID")
        if spreadsheet:
            from sheets_sync import sync
            reports.set_sheet_status("starting", None)
            Thread(target=sync, args=(reports, stop, spreadsheet), daemon=True).start()
        monitor(cv2, detector, config, urls, reports, args.fps, stop)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
