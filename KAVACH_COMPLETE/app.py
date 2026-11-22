from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

BASE_DIR=Path(__file__).resolve().parent
load_dotenv(BASE_DIR/".env")

from kavach.core import empty_events, estimate_population, score_threat
from kavach.feeds import load_all_feeds, demo_events
from kavach.storage import init_db, get_sos
from kavach.ui import (
    inject_theme,header,render_command_centre,render_alert_centre,
    render_citizen,render_rescue,render_sos_console,render_data_notes,render_test_page,
    render_satellite_data_lab
)

st.set_page_config(page_title="KAVACH | Space-Based Disaster Shield",page_icon="🛡️",layout="wide",initial_sidebar_state="expanded")
inject_theme()
init_db()
header()

with st.sidebar:
    st.markdown("## 🛡️ KAVACH")
    st.caption("Space-Based Disaster Shield")
    page=st.radio("Navigation",[
        "Command Centre","Alert Centre","Citizen Safety","Rescue & Help","SOS Console",
        "Satellite Data Lab","Data & Methodology","Prototype Tests"
    ])
    st.divider()
    st.markdown("### Monitoring controls")
    include_demo=st.toggle("Include Bhopal demo scenario",value=True,help="Adds the pitch-deck Bhopal example as SIMULATED data. It is not a live incident.")
    auto_density=st.number_input("Live-event population density assumption (people/km²)",min_value=0,max_value=50000,value=1200,step=100,
        help="Used only for a rough circular-area estimate. Replace with WorldPop/GHSL raster analysis for credible exposure.")
    st.caption("The density assumption is a model input, not observed population data.")
    refresh=st.button("↻ Refresh data feeds",use_container_width=True)
    st.divider()
    st.caption(f"Last app run: {datetime.now().strftime('%d %b %Y · %H:%M:%S')}")
    st.caption("Student prototype · not an official warning service")

@st.cache_data(ttl=240,show_spinner=False)
def cached_live_feeds():
    return load_all_feeds()

if refresh:
    cached_live_feeds.clear()
    st.rerun()

with st.spinner("Connecting to public disaster data feeds..."):
    live_events,statuses=cached_live_feeds()

events=live_events.copy() if live_events is not None else empty_events()
if not events.empty:
    # Explicitly modelled live exposure approximation, not a population raster.
    for i,r in events.iterrows():
        if pd.isna(r.get("population_exposed")):
            area=3.1415926535*float(r.get("danger_radius_km",5))**2
            pop=estimate_population(float(r.get("danger_radius_km",5)),auto_density)
            events.loc[i,"population_exposed"]=pop
            events.loc[i,"population_basis"]=f"Circle area × user density assumption ({auto_density}/km²)"
            events.loc[i,"threat_score"]=score_threat(r.hazard,r.severity,r.value,pop)
if include_demo:
    events=pd.concat([events,demo_events()],ignore_index=True)
if events.empty:
    events=empty_events()

# Keep a stable index for selectboxes.
if not events.empty:
    events=events.reset_index(drop=True)

if page=="Command Centre":
    render_command_centre(events,statuses,include_demo)
elif page=="Alert Centre":
    render_alert_centre(events)
elif page=="Citizen Safety":
    render_citizen(events)
elif page=="Rescue & Help":
    render_rescue(events)
elif page=="SOS Console":
    render_sos_console()
elif page=="Satellite Data Lab":
    render_satellite_data_lab()
elif page=="Data & Methodology":
    render_data_notes(statuses)
else:
    render_test_page(events)

st.divider()
st.markdown(
    "<div style='text-align:center;color:#A9BCCB;font-size:.78rem'>"
    "KAVACH · The Insomni Hacks · ASTRA 2026 · DETECT · LOCATE · ASSESS · ALERT · GUIDE"
    "<br>Prototype only. Follow official NDMA, SDMA, IMD, NCS and local authority guidance.</div>",
    unsafe_allow_html=True
)
