from __future__ import annotations
import os, requests
from .core import haversine_km

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

def find_nearby_help(lat, lon, radius_m=15000):
    query=f"""[out:json][timeout:20];
    (
      node["amenity"~"hospital|clinic|fire_station|police|shelter"](around:{int(radius_m)},{lat},{lon});
      way["amenity"~"hospital|clinic|fire_station|police|shelter"](around:{int(radius_m)},{lat},{lon});
      relation["amenity"~"hospital|clinic|fire_station|police|shelter"](around:{int(radius_m)},{lat},{lon});
    ); out center tags;"""
    last_error=None
    for endpoint in OVERPASS_URLS:
        try:
            r=requests.post(endpoint,data=query,headers={"User-Agent":"KAVACH-ASTRA2026-student-prototype/2.0"},timeout=25)
            r.raise_for_status()
            elements=r.json().get("elements",[])
            results=[]
            for e in elements:
                tags=e.get("tags",{})
                lat2=e.get("lat",e.get("center",{}).get("lat"))
                lon2=e.get("lon",e.get("center",{}).get("lon"))
                if lat2 is None or lon2 is None: continue
                kind=tags.get("amenity","facility")
                results.append({
                    "name":tags.get("name","Unnamed mapped facility"),"type":kind,
                    "latitude":float(lat2),"longitude":float(lon2),
                    "distance_km":haversine_km(lat,lon,lat2,lon2),
                    "address":", ".join(x for x in [tags.get("addr:suburb"),tags.get("addr:city")] if x)
                })
            return sorted(results,key=lambda x:x["distance_km"]), f"OpenStreetMap: {len(results)} facility/facilities"
        except Exception as e:
            last_error=e
    return [], f"Facility lookup unavailable: {type(last_error).__name__ if last_error else 'Error'}: {last_error}"

def get_osrm_route(start_lat,start_lon,end_lat,end_lon):
    url=f"https://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
    try:
        r=requests.get(url,params={"overview":"full","geometries":"geojson","steps":"false"},
            headers={"User-Agent":"KAVACH-ASTRA2026-student-prototype/2.0"},timeout=20)
        r.raise_for_status()
        data=r.json()
        if data.get("code")!="Ok" or not data.get("routes"): return None,"No route returned"
        route=data["routes"][0]
        return {"distance_km":route["distance"]/1000,"duration_min":route["duration"]/60,
                "coordinates":[[p[1],p[0]] for p in route["geometry"]["coordinates"]]}, "OSRM public demo route estimate"
    except Exception as e:
        return None,f"OSRM unavailable: {type(e).__name__}: {e}"

def send_twilio_sms(to_number, body):
    sid=os.getenv("TWILIO_ACCOUNT_SID","").strip()
    token=os.getenv("TWILIO_AUTH_TOKEN","").strip()
    from_number=os.getenv("TWILIO_FROM_NUMBER","").strip()
    if not (sid and token and from_number):
        return False,"Twilio not configured. Add account SID, auth token and sender number to .env."
    try:
        from requests.auth import HTTPBasicAuth
        url=f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        r=requests.post(url,data={"To":to_number,"From":from_number,"Body":body},
            auth=HTTPBasicAuth(sid,token),timeout=20)
        if r.status_code >= 400: return False,f"Twilio rejected request ({r.status_code}): {r.text[:300]}"
        return True,"SMS accepted by Twilio API. Delivery is subject to account, sender and carrier rules."
    except Exception as e:
        return False,f"SMS error: {type(e).__name__}: {e}"
