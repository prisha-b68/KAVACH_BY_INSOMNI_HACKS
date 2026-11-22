# KAVACH — Space-Based Disaster Shield
**The Insomni Hacks | ASTRA 2026**

KAVACH is an India-focused student prototype that brings public disaster observations, map visualisation, transparent risk heuristics, geo-fenced alert demonstrations, citizen test-location checks, local SOS logging and nearby-help routing into one Streamlit web application.

## What's in this improved build

- **National Command Centre:** fire, flood and earthquake incident counts; source-connectivity status; threat-ranked incident queue; incident register; SOS pins; switchable dark operations and satellite imagery map layers.
- **Alert Centre:** inspect events, test a user-entered location against a prototype danger/warning radius, generate English/Hindi messages, request browser notifications, play a local siren, use browser speech, log test alerts and optionally send consent-confirmed Twilio test SMS.
- **Citizen Safety:** manually enter a location, see a prototype proximity status, look up mapped facilities outside the prototype danger circle, request an OSRM route estimate and submit a test SOS.
- **Rescue & Help:** search OpenStreetMap for mapped hospitals, clinics, fire stations, police and shelters; calculate a public OSRM driving-route estimate.
- **SOS Console:** view locally stored SOS submissions and update their workflow status.
- **Satellite Data Lab:** upload a CSV, inspect data quality, map date/category columns, filter records, view dark-themed charts and coordinate plots, and export the filtered CSV.
- **Data & Methodology:** source status and limitations are explained in the app.
- **Prototype Tests:** deterministic geofence checks and a fire-hotspot clustering smoke test.
- **Consistent KAVACH styling:** navy/teal surfaces, gold/cyan accents, readable widget labels, dark Plotly charts, and a root-level `.streamlit/config.toml`.

## Data feeds and setup requirements

| Hazard / service | Adapter in this project | What it actually provides |
|---|---|---|
| Fire | NASA FIRMS VIIRS | Satellite thermal hotspots; requires a free FIRMS MAP_KEY. A hotspot is not automatically a confirmed fire. |
| Earthquake | USGS GeoJSON | Earthquake catalogue records in India's approximate bounding box. Magnitude is not local shaking intensity. |
| Flood | NASA EONET and GDACS RSS | Event-catalogue / alert records; not flood depth, water level or validated inundation polygons. |
| Indian seismic feed | Optional `NCS_FEED_URL` | Only if your team obtains an authorised JSON/GeoJSON endpoint. No endpoint is guessed. |
| Nearby facilities | OpenStreetMap Overpass | Mapped facilities; coverage and current operational status are not guaranteed. |
| Route estimate | Public OSRM demo router | Route distance and modelled duration; not live traffic or confirmed responder ETA. |
| SMS | Optional Twilio | Requires valid credentials, sender configuration and any required recipient verification. |

The Bhopal scenario is included as **SIMULATED** pitch-deck demo data. It is not a live incident. Live population exposure is a configurable density-based circle approximation, not a WorldPop/GHSL raster. Danger/warning radii and threat scores are transparent prototype heuristics, not official perimeters, forecasts or evacuation orders.

## Windows setup (beginner friendly)

1. Install Python 3.11 or 3.12 from <https://www.python.org/downloads/>. During installation, enable **Add Python to PATH**.
2. Extract this ZIP. Open the extracted `KAVACH_COMPLETE` folder in VS Code (the folder containing `app.py`).
3. In VS Code choose **Terminal → New Terminal** and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this in the same terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

4. Copy `.env.example` to `.env`. Add your NASA FIRMS MAP_KEY if you have one. Leave Twilio and NCS values blank until correctly configured. Never share `.env` or publish it to GitHub.
5. Start the web app:

```powershell
python -m streamlit run app.py
```

6. Open <http://localhost:8501> in your browser. The theme config is already in `.streamlit/config.toml`; keep `.streamlit` beside `app.py`, not inside the `kavach` package.

You can also double-click `START_KAVACH.bat` after installing the requirements and activating/configuring your environment.

## Run the checks

```powershell
python -m compileall -q app.py kavach tests
python -m unittest discover -s tests -v
```

## Suggested four-person team split

- **Member 1 — UI/UX:** Command Centre, responsive layout, charts, map presentation.
- **Member 2 — Data feeds:** NASA FIRMS, USGS, EONET/GDACS connectivity and source diagnostics.
- **Member 3 — GIS and analysis:** coordinate validation, hotspot clustering, geofencing, exposure assumptions and methodology.
- **Member 4 — Alerts and response workflow:** browser alert demo, SMS configuration, citizen safety, SOS console and facility routing.

Use one shared Git repository. Avoid editing the same file simultaneously; review changes before merging.

## Important safety and prototype limits

KAVACH is **not** an official warning service and must not be used to make real emergency decisions. Browser notifications/siren/speech run only in the open browser session; they are not background Web Push or government Cell Broadcast. SOS reports are stored in the app's local SQLite database and do not dispatch responders. There is no live responder availability, no official NDRF/police/fire dispatch, no Sentinel-1 flood change detection, no WorldPop/GHSL raster exposure analysis, and no NDMA SACHET/Cell Broadcast integration in this build.

For real emergencies in India, contact **112** and follow official NDMA, SDMA, IMD, NCS and local-authority guidance.

## Useful official/project references

- NASA FIRMS: <https://firms.modaps.eosdis.nasa.gov/api/map_key/>
- USGS Earthquake API: <https://earthquake.usgs.gov/fdsnws/event/1/>
- NASA EONET API: <https://eonet.gsfc.nasa.gov/docs/v3>
- GDACS: <https://www.gdacs.org/>
- OpenStreetMap: <https://www.openstreetmap.org/>
- Overpass API: <https://wiki.openstreetmap.org/wiki/Overpass_API>
- OSRM: <https://project-osrm.org/>
