from __future__ import annotations
import os, requests, pandas as pd, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from .core import INDIA_BOUNDS, empty_events, prototype_radius, score_threat

TIMEOUT = 18
HEADERS = {"User-Agent": "KAVACH-ASTRA2026-student-prototype/2.0 (disaster-awareness project)"}

def _event(**kwargs):
    base = {c: None for c in empty_events().columns}
    base.update(kwargs)
    if base["danger_radius_km"] is None or base["warning_radius_km"] is None:
        dr, wr = prototype_radius(base["hazard"], base["value"], base["severity"])
        base["danger_radius_km"], base["warning_radius_km"] = dr, wr
    base["simulated"] = bool(base.get("simulated", False))
    base["population_basis"] = base.get("population_basis") or "Not calculated"
    if base.get("threat_score") is None:
        base["threat_score"] = score_threat(base["hazard"], base["severity"], base["value"], base["population_exposed"])
    return base

def fetch_firms(map_key: str, days=1):
    if not map_key:
        return empty_events(), "No NASA FIRMS key configured"
    west, south, east, north = 68, 6, 98, 37.5
    source = "VIIRS_SNPP_NRT"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{west},{south},{east},{north}/{int(days)}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        from io import StringIO
        raw = pd.read_csv(StringIO(r.text))
        if raw.empty: return empty_events(), "Connected; no fire detections in selected period"
        # FIRMS field names can vary slightly by product.
        lat_col = next((c for c in ["latitude","lat"] if c in raw.columns), None)
        lon_col = next((c for c in ["longitude","lon"] if c in raw.columns), None)
        if not lat_col or not lon_col: return empty_events(), "FIRMS response did not contain expected coordinates"
        from .core import cluster_fire_hotspots
        work = pd.DataFrame({
            "latitude": pd.to_numeric(raw[lat_col], errors="coerce"),
            "longitude": pd.to_numeric(raw[lon_col], errors="coerce"),
            "frp": pd.to_numeric(raw["frp"], errors="coerce") if "frp" in raw.columns else 0,
            "confidence": raw["confidence"].astype(str) if "confidence" in raw.columns else "unknown",
            "observed": (raw["acq_date"].astype(str) + " " + raw["acq_time"].astype(str))
                        if "acq_date" in raw.columns and "acq_time" in raw.columns else "FIRMS observation"
        }).dropna(subset=["latitude","longitude"])
        clusters = cluster_fire_hotspots(work, radius_km=8.0)
        rows = []
        for i, x in clusters.iterrows():
            conf = str(x["confidence"]).lower()
            severity = "High" if "h" in conf or "high" in conf else "Medium" if "n" in conf or "nominal" in conf else "Low"
            frp = float(x["frp_sum"])
            dr, wr = prototype_radius("Fire", frp, severity)
            rows.append(_event(
                id=f"FIRMS-CLUSTER-{i}-{round(float(x['latitude']),4)}-{round(float(x['longitude']),4)}",
                hazard="Fire", place=f"Fire cluster · {int(x['hotspot_count'])} hotspot(s)",
                latitude=float(x["latitude"]), longitude=float(x["longitude"]),
                observed=str(x["observed"]), source="NASA FIRMS VIIRS + KAVACH clustering",
                severity=severity, value=frp,
                detail=f"Clustered {int(x['hotspot_count'])} satellite hotspot(s) within an approximately 8 km grouping radius; summed FRP={frp:.1f} MW; confidence={x['confidence']}. Thermal anomalies require field verification and are not automatically confirmed forest fires.",
                url="https://firms.modaps.eosdis.nasa.gov/", danger_radius_km=dr, warning_radius_km=wr
            ))
        return pd.DataFrame(rows), f"Connected; {len(raw)} hotspot(s) grouped into {len(rows)} incident cluster(s)"
    except Exception as e:
        return empty_events(), f"FIRMS unavailable: {type(e).__name__}: {e}"

def fetch_usgs(days=7, min_magnitude=2.5):
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {"format":"geojson","starttime":f"{(pd.Timestamp.utcnow()-pd.Timedelta(days=days)).date()}",
              "minmagnitude":min_magnitude,"minlatitude":6,"maxlatitude":37.5,
              "minlongitude":68,"maxlongitude":98,"orderby":"time"}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
        features = r.json().get("features", [])
        rows = []
        for f in features:
            p = f.get("properties",{}); g = f.get("geometry",{}).get("coordinates",[])
            if len(g) < 3: continue
            lon, lat, depth = g[0], g[1], g[2]
            mag = p.get("mag")
            sev = "Critical" if mag is not None and mag >= 6 else "High" if mag is not None and mag >= 5 else "Medium" if mag is not None and mag >= 4 else "Low"
            dr, wr = prototype_radius("Earthquake", mag, sev)
            rows.append(_event(
                id=f"USGS-{f.get('id')}", hazard="Earthquake", place=p.get("place","Earthquake event"),
                latitude=lat, longitude=lon, observed=pd.to_datetime(p.get("time"),unit="ms",utc=True).isoformat(),
                source="USGS Earthquake GeoJSON", severity=sev, value=mag,
                detail=f"Magnitude {mag}; depth {depth} km. Magnitude is not the same as local shaking intensity.",
                url=p.get("url"), danger_radius_km=dr, warning_radius_km=wr
            ))
        return pd.DataFrame(rows) if rows else empty_events(), f"Connected; {len(rows)} earthquake event(s)"
    except Exception as e:
        return empty_events(), f"USGS unavailable: {type(e).__name__}: {e}"

def fetch_eonet():
    url = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
        events = r.json().get("events", [])
        rows = []
        for ev in events:
            cats = [c.get("title","") for c in ev.get("categories",[])]
            title = " ".join(cats + [ev.get("title","")]).lower()
            if not any(k in title for k in ["flood","flooding"]): continue
            geom = ev.get("geometry",[])
            if not geom: continue
            g = geom[-1]; coords = g.get("coordinates",[])
            if g.get("type") == "Point" and len(coords)>=2:
                lon, lat = coords[0], coords[1]
            elif g.get("type") == "Polygon" and coords and coords[0]:
                ring = coords[0]; lon = sum(p[0] for p in ring)/len(ring); lat = sum(p[1] for p in ring)/len(ring)
            else: continue
            if not (6 <= lat <= 37.5 and 68 <= lon <= 98): continue
            rows.append(_event(
                id=f"EONET-{ev.get('id')}", hazard="Flood", place=ev.get("title","Flood event"),
                latitude=lat, longitude=lon, observed=g.get("date","Unknown"),
                source="NASA EONET", severity="Unrated", value=None,
                detail="NASA EONET event-catalogue record. This is not a live flood-depth, water-level or inundation product.",
                url=(ev.get("sources") or [{}])[0].get("url","https://eonet.gsfc.nasa.gov/"),
                danger_radius_km=5, warning_radius_km=12
            ))
        return pd.DataFrame(rows) if rows else empty_events(), f"Connected; {len(rows)} India flood catalogue event(s)"
    except Exception as e:
        return empty_events(), f"EONET unavailable: {type(e).__name__}: {e}"

def fetch_gdacs():
    url = "https://www.gdacs.org/xml/rss.xml"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
        root = ET.fromstring(r.content)
        rows = []
        for item in root.findall(".//item"):
            title = item.findtext("title","GDACS event")
            desc = item.findtext("description","")
            link = item.findtext("link","")
            # GeoRSS point is commonly "lat lon".
            point = item.findtext("{http://www.georss.org/georss}point")
            if not point: continue
            parts = point.split()
            if len(parts) < 2: continue
            lat, lon = float(parts[0]), float(parts[1])
            if not (6 <= lat <= 37.5 and 68 <= lon <= 98): continue
            low = title.lower()
            hazard = "Flood" if "flood" in low else "Earthquake" if "earthquake" in low else "Fire" if "fire" in low else None
            if not hazard: continue
            rows.append(_event(
                id=f"GDACS-{link or title}", hazard=hazard, place=title, latitude=lat, longitude=lon,
                observed="GDACS feed time", source="GDACS RSS", severity="Unrated", value=None,
                detail=desc[:700], url=link
            ))
        return pd.DataFrame(rows) if rows else empty_events(), f"Connected; {len(rows)} GDACS India event(s)"
    except Exception as e:
        return empty_events(), f"GDACS unavailable: {type(e).__name__}: {e}"

def fetch_optional_ncs():
    url = os.getenv("NCS_FEED_URL","").strip()
    if not url: return empty_events(), "Not configured (no authorised NCS feed URL supplied)"
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
        data = r.json()
        features = data.get("features",[]) if isinstance(data,dict) else data
        rows=[]
        for i, f in enumerate(features):
            p=f.get("properties",{}); geom=f.get("geometry",{}); coords=geom.get("coordinates",[])
            if len(coords)<2: continue
            lon,lat=coords[0],coords[1]
            if not (6<=lat<=37.5 and 68<=lon<=98): continue
            mag=p.get("mag",p.get("magnitude"))
            rows.append(_event(id=f"NCS-{p.get('id',i)}",hazard="Earthquake",place=p.get("place","NCS earthquake"),
                latitude=lat,longitude=lon,observed=p.get("time","Unknown"),source="Configured NCS feed",
                severity="Unrated",value=mag,detail="Configured external NCS feed; verify source and terms.",
                url=p.get("url","https://seismo.gov.in/")))
        return pd.DataFrame(rows) if rows else empty_events(), f"Configured; {len(rows)} NCS event(s)"
    except Exception as e:
        return empty_events(), f"NCS feed error: {type(e).__name__}: {e}"

def demo_events():
    # Pitch-deck scenario: explicitly simulated, never merged silently with verified live observations.
    return pd.DataFrame([_event(
        id="DEMO-BHOPAL-FIRE-001", hazard="Fire", place="SIMULATED — Forest fire near Bhopal",
        latitude=23.2599, longitude=77.4126, observed="Demo scenario · 21 Nov 2026",
        source="KAVACH pitch-deck simulation", severity="Critical", value=510,
        detail="SIMULATED: 21 clustered hotspots; total FRP 510 MW; 21 km danger radius; threat score 83. Population estimate 18.9 lakh is scenario data from the pitch deck, not a live population calculation.",
        url="", simulated=True, danger_radius_km=21, warning_radius_km=35,
        population_exposed=1890000, population_basis="Pitch-deck scenario value (simulated)", threat_score=83
    )])

def load_all_feeds():
    key = os.getenv("NASA_FIRMS_MAP_KEY","").strip()
    firms, s_firms = fetch_firms(key)
    quakes, s_usgs = fetch_usgs()
    floods, s_eonet = fetch_eonet()
    gdacs, s_gdacs = fetch_gdacs()
    ncs, s_ncs = fetch_optional_ncs()
    frames=[x for x in [firms,quakes,floods,gdacs,ncs] if x is not None and not x.empty]
    events=pd.concat(frames,ignore_index=True) if frames else empty_events()
    if not events.empty:
        events=events.drop_duplicates(subset=["id"],keep="first").reset_index(drop=True)
    return events, {
        "NASA FIRMS":s_firms, "USGS":s_usgs, "NASA EONET":s_eonet,
        "GDACS":s_gdacs, "NCS India":s_ncs
    }
