"""Draw counting lines and zones on a fresh image from each camera."""
import argparse
import json
import os
from pathlib import Path
from threading import Event
import time

from counting import cross
from vehicle_monitor import Stream, camera_settings, stream_url

COLORS = {
    "road": (66, 205, 250),
    "fuel_road": (66, 205, 250),
    "driveway": (255, 174, 73),
    "door": (210, 125, 250),
    "at_pumps": (73, 223, 165),
    "queue": (66, 205, 250),
    "bypass_zone": (255, 174, 73),
}


def pixel(frame, point):
    height, width = frame.shape[:2]
    return round(point[0] * (width - 1)), round(point[1] * (height - 1))


def draw_geometry(cv, frame, role, spec):
    shapes = (("at_pumps", "Pumps"), ("queue", "Queue"), ("bypass_zone", "Bypass")) if role == "fuel" else (
        ("line", "Highway trial" if role == "fuel_road" else role.capitalize()),)
    for key, label in shapes:
        points = spec.get(key, [])
        if not points:
            continue
        vertices = [pixel(frame, point) for point in points]
        color = COLORS[key if role == "fuel" else role]
        pairs = zip(vertices, vertices[1:] + (vertices[:1] if role == "fuel" else []))
        for start, finish in pairs:
            cv.line(frame, start, finish, color, 2, cv.LINE_AA)
        x, y = vertices[0]
        cv.putText(frame, label, (x, max(18, y - 6)), cv.FONT_HERSHEY_SIMPLEX, .5, color, 2, cv.LINE_AA)


def snapshot(cv, role):
    stop = Event()
    reader = Stream(cv, stream_url(role), stop)
    reader.worker.start()
    deadline = time.monotonic() + 14
    try:
        while time.monotonic() < deadline:
            sample = reader.read()
            if sample:
                return sample[2]
            time.sleep(.1)
        raise ValueError(f"No video from {role}. Verify that its VLC feed and login work on this PC.")
    finally:
        stop.set()
        reader.worker.join(timeout=4)


def choose(cv, image, title, instruction, mode, optional=False, prior=None):
    height, width = image.shape[:2]
    scale = min(1.0, 950 / width, 650 / height)
    width, height = round(width * scale), round(height * scale)
    frame = cv.resize(image, (width, height))
    window = "OM AI Calibration"
    cv.namedWindow(window, cv.WINDOW_AUTOSIZE)
    cv.setWindowTitle(window, f"OM AI Calibration - {title}")
    selected = []
    message = ""
    fixed = {"line": 2, "side": 1}.get(mode)

    def mouse(event, x, y, *_):
        if event == cv.EVENT_LBUTTONDOWN and 0 <= x < width and 0 <= y < height:
            if fixed is None or len(selected) < fixed:
                selected.append([x / (width - 1), y / (height - 1)])

    cv.setMouseCallback(window, mouse)
    while True:
        canvas = frame.copy()
        if prior:
            draw_geometry(cv, canvas, prior[0], prior[1])
        positions = [pixel(canvas, point) for point in selected]
        for start, end in zip(positions, positions[1:]):
            cv.line(canvas, start, end, (0, 218, 255), 2, cv.LINE_AA)
        if mode == "polygon" and len(positions) >= 3:
            cv.line(canvas, positions[-1], positions[0], (0, 218, 255), 1, cv.LINE_AA)
        for position in positions:
            cv.circle(canvas, position, 5, (0, 218, 255), -1, cv.LINE_AA)
        canvas = cv.copyMakeBorder(canvas, 0, 85, 0, max(0, 680 - width), cv.BORDER_CONSTANT, value=(23, 25, 33))
        keys = "Enter: accept   R: reset   Backspace: undo   Esc: cancel"
        if optional:
            keys += "   S: skip"
        for index, line in enumerate((f"{title}  |  {instruction}", keys, message)):
            cv.putText(canvas, line, (9, height + 22 + index * 24), cv.FONT_HERSHEY_SIMPLEX,
                       .51, (240, 242, 245), 1, cv.LINE_AA)
        cv.imshow(window, canvas)
        key = cv.waitKey(40)
        if key == 27 or cv.getWindowProperty(window, cv.WND_PROP_VISIBLE) < 1:
            raise KeyboardInterrupt
        if key in (ord("r"), ord("R")):
            selected.clear()
            message = ""
        if key in (8, 127) and selected:
            selected.pop()
        if optional and key in (ord("s"), ord("S")):
            return []
        if key not in (10, 13):
            continue
        if fixed is not None and len(selected) != fixed or fixed is None and len(selected) < 3:
            message = "Click the required points first."
            continue
        if mode == "line" and sum((a - b) ** 2 for a, b in zip(*selected)) < .02 ** 2:
            message = "Draw a longer line."
            continue
        if mode == "polygon":
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(selected, selected[1:] + selected[:1]))
            if abs(area) < .0001:
                message = "Outline the zone using points around its perimeter."
                continue
        if mode == "side" and abs(cross(*prior[1]["line"], selected[0])) < .0005:
            message = "Choose a point farther away from the line."
            continue
        return selected


def crossing(cv, frame, role, instruction, optional=False):
    line = choose(cv, frame, role.capitalize(), instruction, "line", optional)
    if not line:
        return None
    spec = {"confirmed": True, "line": line}
    if role in ("driveway", "door"):
        point, = choose(cv, frame, role.capitalize(), "Click a point on the inside side.",
                         "side", prior=(role, spec))
        spec["inside_side"] = 1 if cross(*line, point) > 0 else -1
    return spec


def automatic_config(output):
    preset = output.with_name("calibration-preset.json")
    if not preset.is_file():
        raise ValueError("Run manual calibration first or provide a local calibration-preset.json.")
    return json.loads(preset.read_text(encoding="utf-8-sig"))


def save_and_verify(output, config):
    camera_settings(config)
    temporary = output.with_suffix(".new")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    if saved != config:
        raise ValueError("Saved calibration does not match the settings that were written.")
    camera_settings(saved)
    print(f"Calibration saved and verified: {output}", flush=True)


def automatic(cv, output, replace, add_fuel_road=False):
    existing = output.is_file() and not replace
    config = json.loads(output.read_text(encoding="utf-8-sig")) if existing else automatic_config(output)
    changed = add_fuel_road and "fuel_road" not in config
    if changed:
        fuel_road = automatic_config(output).get("fuel_road")
        if not fuel_road:
            raise ValueError("The local calibration preset has no highway line.")
        config["fuel_road"] = fuel_road
    camera_settings(config)
    for channel, role in ((1, "road"), (6, "fuel"), (3, "door")):
        print(f"Checking live Channel {channel} ({role})...", flush=True)
        frame = snapshot(cv, role)
        height, width = frame.shape[:2]
        if width < 160 or height < 120:
            raise ValueError(f"Channel {channel} returned an unexpectedly small frame.")
        print(f"PASS: Channel {channel} decoded a {width} x {height} frame.", flush=True)
    if existing and not changed:
        print(f"PASS: Existing calibration loaded and validated: {output}", flush=True)
    else:
        save_and_verify(output, config)
        print("Preset applied. Review the line and pump overlays before relying on the counts.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--automatic", action="store_true")
    parser.add_argument("--replace", action="store_true", help="Replace the existing calibration in automatic mode.")
    parser.add_argument("--add-fuel-road", action="store_true", help="Add the highway trial to saved calibration.")
    args = parser.parse_args()
    os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
    import cv2 as cv

    try:
        if args.automatic:
            automatic(cv, args.output, args.replace, args.add_fuel_road)
            return
        print("Connecting to Channel 1. Use the OM AI Calibration window to click points.", flush=True)
        side = snapshot(cv, "road")
        config = {
            "road": crossing(cv, side, "road", "Click two endpoints across the travel lanes."),
            "driveway": crossing(cv, side, "driveway", "Click two endpoints just inside the driveway mouth."),
        }
        fuel = snapshot(cv, "fuel")
        pumps = choose(cv, fuel, "Pump area", "Outline the ground where vehicles stop at the pumps.", "polygon")
        queue = choose(cv, fuel, "Fuel queue", "Outline the visible waiting lane away from the pumps.",
                       "polygon", optional=True, prior=("fuel", {"at_pumps": pumps}))
        bypass = choose(cv, fuel, "Bypass lane", "Outline a separate visible bypass lane, if applicable.",
                        "polygon", optional=True, prior=("fuel", {"at_pumps": pumps, "queue": queue}))
        config["fuel"] = {"confirmed": True, "at_pumps": pumps, "queue": queue, "bypass_zone": bypass,
                          "wait_seconds": 15, "motion_radius": .015}
        fuel_road = crossing(cv, fuel, "fuel_road",
                             "Draw across the visible highway lanes, or press S to skip.", True)
        if fuel_road:
            config["fuel_road"] = fuel_road
        if stream_url("door"):
            outdoor = snapshot(cv, "door")
            door = crossing(cv, outdoor, "door", "Mark the doorway crossing if visible. Otherwise press S.", True)
            if door:
                config["door"] = door
        save_and_verify(args.output, config)
    except KeyboardInterrupt:
        parser.exit(1, "Calibration canceled.\n")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"{exc}\n")
    finally:
        if not args.automatic:
            cv.destroyAllWindows()


if __name__ == "__main__":
    main()
