"""Count vehicle tracks using calibrated image-space geometry."""
from dataclasses import dataclass, field
from math import dist


def cross(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])


def inside(point, polygon):
    x, y = point
    hit = False
    for a, b in zip(polygon, polygon[1:]+polygon[:1]):
        if (a[1] > y) != (b[1] > y):
            hit ^= x < a[0]+(b[0]-a[0])*(y-a[1])/(b[1]-a[1])
    return hit


@dataclass
class Vehicle:
    point: tuple
    seen: float
    observations: int = 1
    velocity: tuple = (0., 0.)
    side: int = 0
    anchor: tuple | None = None
    crossing_at: float = float("-inf")
    zone: str = "other"
    parked_at: float = 0.
    parked_point: tuple = (0., 0.)


@dataclass
class Counter:
    role: str
    calibration: dict
    vehicles: list = field(default_factory=list)

    def clear(self):
        self.vehicles.clear()

    def step(self, now, points):
        """Return named events and, for fuel, the latest zone counts."""
        self.vehicles = [v for v in self.vehicles if now-v.seen <= 1.2]
        candidates = []
        for i, vehicle in enumerate(self.vehicles):
            elapsed = now-vehicle.seen
            predicted = tuple(p+d*min(elapsed, .6) for p,d in zip(vehicle.point,vehicle.velocity))
            for j, point in enumerate(points):
                gap = dist(predicted,point)
                if gap <= min(.14,.045+.17*elapsed):
                    candidates.append((gap,i,j))
        used_tracks, used_points = set(), set()
        visible = []
        events = []
        for _, i, j in sorted(candidates):
            if i in used_tracks or j in used_points:
                continue
            used_tracks.add(i)
            used_points.add(j)
            vehicle, point = self.vehicles[i], points[j]
            elapsed = max(now-vehicle.seen,.01)
            if elapsed > .85:
                vehicle.side, vehicle.anchor = 0, None
                vehicle.zone = "other"
                vehicle.observations = 0
            vehicle.velocity = tuple(.35*old+.65*(b-a)/elapsed
                                     for old,a,b in zip(vehicle.velocity,vehicle.point,point))
            vehicle.point, vehicle.seen = point, now
            vehicle.observations += 1
            visible.append(vehicle)
        for j, point in enumerate(points):
            if j not in used_points:
                vehicle = Vehicle(point,now)
                self.vehicles.append(vehicle)
                visible.append(vehicle)
        occupancy = dict(waiting=0, queue_moving=0, at_pumps=0, bypass_zone=0)
        for vehicle in visible:
            if self.role == "fuel":
                zone = self.fuel_zone(vehicle.point)
                if zone != vehicle.zone or dist(vehicle.parked_point,vehicle.point) > self.calibration["motion_radius"]:
                    vehicle.parked_at, vehicle.parked_point = now, vehicle.point
                vehicle.zone = zone
                if vehicle.observations < 2:
                    continue
                if zone == "queue":
                    key = "waiting" if now-vehicle.parked_at >= self.calibration["wait_seconds"] else "queue_moving"
                    occupancy[key] += 1
                elif zone != "other":
                    occupancy[zone] += 1
            else:
                event = self.crossing(vehicle,now)
                if event:
                    events.append(event)
        return events, occupancy if self.role == "fuel" else None

    def fuel_zone(self, point):
        for name in ("at_pumps","queue","bypass_zone"):
            if inside(point,self.calibration.get(name,[])):
                return name
        return "other"

    def crossing(self, vehicle, now):
        a, b = self.calibration["line"]
        signed = cross(a,b,vehicle.point)/dist(a,b)
        if abs(signed) <= self.calibration.get("line_band",.008):
            return None
        side = 1 if signed > 0 else -1
        old, anchor = vehicle.side, vehicle.anchor
        vehicle.side, vehicle.anchor = side, vehicle.point
        if not old or old == side or now-vehicle.crossing_at < .8:
            return None
        p = vehicle.point
        denominator = cross(anchor,p,b)-cross(anchor,p,a)
        if abs(denominator) < 1e-10:
            return None
        position = -cross(anchor,p,a)/denominator
        if not 0 <= position <= 1:
            return None
        vehicle.crossing_at = now
        if self.role in ("road", "fuel_road"):
            direction = "negative_to_positive" if side == 1 else "positive_to_negative"
            return f"{self.role}_{direction}"
        if self.role == "door":
            return "door_entered" if side == self.calibration["inside_side"] else "door_exited"
        return "entered" if side == self.calibration["inside_side"] else "exited"
