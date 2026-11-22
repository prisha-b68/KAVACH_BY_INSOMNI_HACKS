from __future__ import annotations
from datetime import datetime, timezone
import math
import pandas as pd

INDIA_BOUNDS = {"west": 68.0, "south": 6.0, "east": 98.0, "north": 37.5}
COLUMNS = [
    "id", "hazard", "place", "latitude", "longitude", "observed", "source",
    "severity", "value", "detail", "url", "simulated", "danger_radius_km",
    "warning_radius_km", "population_exposed", "population_basis", "threat_score"
]

def empty_events() -> pd.DataFrame:
    return pd.DataFrame(columns=COLUMNS)

def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0088
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(min(1.0, math.sqrt(a)))

def in_india(lat, lon) -> bool:
    b = INDIA_BOUNDS
    try:
        return b["south"] <= float(lat) <= b["north"] and b["west"] <= float(lon) <= b["east"]
    except (TypeError, ValueError):
        return False

def geofence_status(person_lat, person_lon, event_lat, event_lon, danger_km, warning_km):
    distance = haversine_km(person_lat, person_lon, event_lat, event_lon)
    if distance <= float(danger_km):
        status = "DANGER"
    elif distance <= float(warning_km):
        status = "WARNING"
    else:
        status = "SAFE"
    return status, distance

def prototype_radius(hazard: str, value=None, severity="Unrated"):
    """Heuristic demo radii only; not scientifically validated warning perimeters."""
    try:
        v = float(value) if value is not None and pd.notna(value) else None
    except (TypeError, ValueError):
        v = None
    h = str(hazard).lower()
    if h == "earthquake":
        m = v if v is not None else 3.0
        danger = max(3.0, min(30.0, 2.5 * (m ** 1.35)))
        return round(danger, 1), round(danger * 2.0, 1)
    if h == "fire":
        danger = 5.0
        if v is not None:
            danger = max(3.0, min(25.0, 3.0 + v / 250.0))
        if str(severity).lower() == "high":
            danger = max(danger, 8.0)
        return round(danger, 1), round(danger * 2.0, 1)
    if h == "flood":
        return 5.0, 12.0
    return 3.0, 8.0

def score_threat(hazard, severity, value=None, population_exposed=None):
    """Transparent 0–100 prototype prioritisation score, not an official risk model."""
    h = str(hazard).lower()
    sev = str(severity).lower()
    base = {"critical": 90, "high": 72, "medium": 48, "low": 25}.get(sev, 35)
    try:
        v = float(value) if value is not None and pd.notna(value) else None
    except (TypeError, ValueError):
        v = None
    if h == "earthquake" and v is not None:
        base = min(100, max(base, int((v - 2.0) * 17)))
    elif h == "fire" and v is not None:
        base = min(100, max(base, int(25 + min(v, 1500) / 25)))
    pop_bonus = 0
    try:
        p = float(population_exposed)
        if p > 0:
            pop_bonus = min(25, int(math.log10(p + 1) * 4))
    except (TypeError, ValueError):
        pass
    return int(max(0, min(100, base * 0.78 + pop_bonus)))

def cluster_fire_hotspots(df: pd.DataFrame, radius_km=8.0) -> pd.DataFrame:
    """Greedy distance clustering; suitable for a small prototype feed."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["latitude","longitude","hotspot_count","frp_sum","confidence","observed","place"])
    points = df.copy().dropna(subset=["latitude","longitude"]).reset_index(drop=True)
    groups = []
    for _, row in points.iterrows():
        assigned = False
        for group in groups:
            clat = sum(x["latitude"] for x in group) / len(group)
            clon = sum(x["longitude"] for x in group) / len(group)
            if haversine_km(row.latitude, row.longitude, clat, clon) <= radius_km:
                group.append(row.to_dict())
                assigned = True
                break
        if not assigned:
            groups.append([row.to_dict()])
    result = []
    for i, group in enumerate(groups, start=1):
        lat = sum(float(x["latitude"]) for x in group) / len(group)
        lon = sum(float(x["longitude"]) for x in group) / len(group)
        frps = []
        confs = []
        for x in group:
            try:
                if pd.notna(x.get("frp")): frps.append(float(x["frp"]))
            except (ValueError, TypeError): pass
            if x.get("confidence") is not None: confs.append(str(x["confidence"]))
        result.append({
            "latitude": lat, "longitude": lon, "hotspot_count": len(group),
            "frp_sum": sum(frps), "confidence": ", ".join(sorted(set(confs))) or "Not supplied",
            "observed": str(group[0].get("observed", "Unknown")),
            "place": f"Fire cluster {i}"
        })
    return pd.DataFrame(result)

def estimate_population(radius_km, density_per_km2):
    area = math.pi * float(radius_km) ** 2
    return max(0, int(area * max(0, float(density_per_km2))))
