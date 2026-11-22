from __future__ import annotations
from .core import geofence_status

def alert_priority(event):
    hazard=str(event.get("hazard","")).lower()
    severity=str(event.get("severity","")).lower()
    try: value=float(event.get("value")) if event.get("value") is not None else None
    except (TypeError,ValueError): value=None
    if hazard=="earthquake":
        if value is not None and value>=5.0: return "HIGH"
        if value is not None and value>=4.0: return "MEDIUM"
    if hazard=="fire":
        if severity in {"critical","high"}: return "HIGH"
        if severity=="medium": return "MEDIUM"
    if hazard=="flood":
        if severity in {"critical","high"}: return "HIGH"
        return "REVIEW"
    return "REVIEW"

def make_message(event, language="English", status="WARNING", distance_km=None):
    hazard=event.get("hazard","disaster")
    place=event.get("place","reported location")
    if language.lower().startswith("h"):
        labels={"DANGER":"खतरा","WARNING":"चेतावनी","SAFE":"सुरक्षित"}
        return f"KAVACH {labels.get(status,status)}: {place} के पास {hazard} की सूचना/अवलोकन मिला है। दूरी: {distance_km:.1f} किमी। स्थानीय प्रशासन और आधिकारिक निर्देशों का पालन करें। यह प्रोटोटाइप अलर्ट है, आधिकारिक चेतावनी नहीं।"
    dist=f" Approx. distance: {distance_km:.1f} km." if distance_km is not None else ""
    return f"KAVACH {status}: {hazard} information/observation near {place}.{dist} Follow official local-authority instructions. Prototype notification only; not an official warning."

def assess_person(event, lat, lon):
    return geofence_status(lat,lon,event["latitude"],event["longitude"],
        event.get("danger_radius_km",5),event.get("warning_radius_km",10))
