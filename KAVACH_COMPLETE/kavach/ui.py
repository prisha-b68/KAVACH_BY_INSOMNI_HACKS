from __future__ import annotations
import html, json
import streamlit as st
import streamlit.components.v1 as components
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import pandas as pd
import plotly.express as px
from .core import haversine_km, geofence_status, estimate_population
from .alerts import alert_priority, make_message, assess_person
from .services import find_nearby_help, get_osrm_route, send_twilio_sms
from .storage import add_sos, get_sos, update_sos_status, add_person, get_people, log_alert, get_alert_log

PALETTE={"navy":"#071522","teal":"#073E45","gold":"#FFB72B","cyan":"#25C9B5","burgundy":"#712A43","text":"#F4F7FB","muted":"#A9BCCB","red":"#FF5C68","blue":"#4BA9E8","green":"#54D6A5"}


def _style_plotly(fig, height=None):
    """Apply KAVACH's dark palette to every Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(7,62,69,0.22)",
        font={"color": PALETTE["text"], "family": "Arial, sans-serif", "size": 13},
        title={"font": {"color": "#FFFFFF", "size": 18}},
        xaxis={"gridcolor": "rgba(169,188,203,0.18)", "zerolinecolor": "rgba(169,188,203,0.25)"},
        yaxis={"gridcolor": "rgba(169,188,203,0.18)", "zerolinecolor": "rgba(169,188,203,0.25)"},
        legend={"font": {"color": PALETTE["text"]}, "bgcolor": "rgba(0,0,0,0)"},
        margin={"l": 28, "r": 24, "t": 58, "b": 32},
    )
    if height:
        fig.update_layout(height=height)
    return fig

def inject_theme():
    st.markdown(f"""
    <style>
    :root {{ color-scheme: dark; }}
    .stApp {{
      background:
        radial-gradient(ellipse at 8% 92%, rgba(37,201,181,.17) 0%, transparent 38%),
        radial-gradient(ellipse at 92% 4%, rgba(113,42,67,.24) 0%, transparent 42%),
        linear-gradient(128deg,#061522 0%,#0b1b2b 48%,#171827 100%);
      color:{PALETTE['text']};
    }}
    [data-testid="stHeader"] {{background:rgba(7,21,34,.82);}}
    [data-testid="stSidebar"] {{background:linear-gradient(180deg,#071522 0%,#0b2932 65%,#10202e 100%);border-right:1px solid rgba(37,201,181,.28);}}
    .block-container {{max-width:1600px;padding-top:1.25rem;padding-bottom:3rem;}}
    h1,h2,h3 {{color:#F4F7FB;letter-spacing:.01em;}}
    h1 {{text-shadow:0 0 24px rgba(255,183,43,.15);}}
    [data-testid="stMetric"] {{background:linear-gradient(145deg,rgba(7,62,69,.66),rgba(17,31,47,.92));border:1px solid rgba(37,201,181,.25);padding:13px 15px;border-radius:14px;}}
    [data-testid="stMetricLabel"] {{color:#B5C9D3;}}
    [data-testid="stMetricValue"] {{color:#FFCA61;}}
    .k-card {{background:linear-gradient(145deg,rgba(12,39,52,.92),rgba(17,27,43,.94));border:1px solid rgba(37,201,181,.23);border-radius:14px;padding:15px 17px;margin-bottom:8px;}}
    .k-muted {{color:#A9BCCB;font-size:.82rem;}}
    .k-eyebrow {{color:#25C9B5;font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;}}
    .k-gold {{color:#FFB72B;}}
    div.stButton>button {{border-radius:10px;border:1px solid rgba(37,201,181,.4);}}
    div[data-testid="stAlert"] {{border-radius:12px;}}
    a {{color:#45D5C5 !important;}}

    /* Native Streamlit widgets: keep text legible on the dark KAVACH surface. */
    [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"] p, label, .stRadio label, .stCheckbox label {{
      color: #E7F0F4 !important;
    }}
    [data-testid="stAlert"] {{
      background: rgba(16,47,58,.92) !important;
      border: 1px solid rgba(37,201,181,.28) !important;
      border-radius: 12px !important;
    }}
    [data-testid="stAlert"] p, [data-testid="stAlert"] span {{ color: #F4F7FB !important; }}
    [data-baseweb="input"] > div, [data-baseweb="select"] > div,
    [data-baseweb="textarea"] > div {{
      background: #F1F5F9 !important; color: #10232D !important;
      border-color: #78909C !important; border-radius: 9px !important;
    }}
    [data-baseweb="input"] input, [data-baseweb="textarea"] textarea {{
      color: #10232D !important; -webkit-text-fill-color: #10232D !important;
    }}
    [data-baseweb="select"] input, [data-baseweb="select"] span {{
      color: #10232D !important; -webkit-text-fill-color: #10232D !important;
    }}
    div.stButton > button, div.stDownloadButton > button,
    div.stFormSubmitButton > button, div.stLinkButton > a {{
      background: linear-gradient(135deg, #0B4650, #12313F) !important;
      color: #F4F7FB !important; border: 1px solid rgba(37,201,181,.48) !important;
      border-radius: 10px !important; font-weight: 650 !important;
    }}
    div.stButton > button:hover, div.stDownloadButton > button:hover,
    div.stFormSubmitButton > button:hover {{
      border-color: #FFB72B !important; color: #FFCA61 !important;
    }}
    [data-testid="stDataFrame"], [data-testid="stTable"] {{
      border: 1px solid rgba(37,201,181,.22) !important; border-radius: 10px !important;
    }}
    [data-testid="stExpander"] {{
      background: rgba(10,35,47,.62) !important; border: 1px solid rgba(37,201,181,.2) !important;
      border-radius: 10px !important;
    }}
    [data-testid="stFileUploader"] section {{
      background: rgba(10,35,47,.72) !important; border: 1px dashed rgba(37,201,181,.45) !important;
    }}
    [data-testid="stFileUploader"] section * {{ color: #E7F0F4 !important; }}
    [data-testid="stTabs"] button {{ color: #DCE8ED !important; }}
    hr {{ border-color: rgba(169,188,203,.28) !important; }}
    </style>
    """,unsafe_allow_html=True)

def header():
    st.markdown(f"""
    <div class="k-card">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
        <div><div class="k-eyebrow">THE INSOMNI HACKS · ASTRA 2026</div>
        <div style="font-size:2rem;font-weight:800;letter-spacing:.04em;color:#FFB72B">🛡️ KAVACH</div>
        <div style="font-size:.93rem;color:#D8E7EA">SPACE-BASED DISASTER SHIELD</div></div>
        <div style="text-align:right;color:#25C9B5;font-weight:700">DETECT · LOCATE · ASSESS · ALERT · GUIDE<br>
        <span style="font-size:.75rem;color:#A9BCCB;font-weight:400">Earth Observation · Disaster Management · Navigation</span></div>
      </div>
    </div>""",unsafe_allow_html=True)

def event_color(row):
    return {"Fire":"#ff5c45","Flood":"#42a5f5","Earthquake":"#ffbf47"}.get(row.get("hazard"),"#c4a4ff")

def build_map(events, sos_rows=None, selected_event=None, route=None, person=None):
    # Start with named layers so judges can switch between operational dark map and imagery.
    m=folium.Map(location=[22.8,79.0],zoom_start=5,tiles=None,control_scale=True)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
        attr="© OpenStreetMap contributors © CARTO", name="Dark operations map",
        subdomains="abcd", max_zoom=19, show=True
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Imagery © Esri, Maxar, Earthstar Geographics", name="Satellite imagery",
        max_zoom=19, show=False
    ).add_to(m)
    if events is not None and not events.empty:
        for _,r in events.iterrows():
            try:
                lat,lon=float(r.latitude),float(r.longitude)
                color=event_color(r)
                simulated=bool(r.get("simulated",False))
                label=f"{r.hazard}: {r.place}"
                popup=f"<b>{html.escape(label)}</b><br>Severity: {html.escape(str(r.severity))}<br>Source: {html.escape(str(r.source))}<br>{'SIMULATED' if simulated else 'Source observation'}"
                folium.CircleMarker([lat,lon],radius=7 if not simulated else 10,color=color,fill=True,fill_opacity=.85,
                    tooltip=label,popup=folium.Popup(popup,max_width=320)).add_to(m)
                if selected_event is not None and str(r.get("id"))==str(selected_event.get("id")):
                    folium.Circle([lat,lon],radius=float(r.get("danger_radius_km",5))*1000,color="#ff435b",fill=True,fill_opacity=.10,
                        tooltip=f"Prototype danger zone: {r.get('danger_radius_km')} km").add_to(m)
                    folium.Circle([lat,lon],radius=float(r.get("warning_radius_km",10))*1000,color="#ffbf47",fill=False,dash_array="7,7",
                        tooltip=f"Prototype warning zone: {r.get('warning_radius_km')} km").add_to(m)
            except Exception: pass
    for s in sos_rows or []:
        folium.Marker([s["latitude"],s["longitude"]],icon=folium.Icon(color="red",icon="warning-sign"),
            tooltip=f"SOS #{s['id']} · {s['status']}").add_to(m)
    if person:
        folium.Marker([person[0],person[1]],icon=folium.Icon(color="green",icon="user"),tooltip="Citizen / test location").add_to(m)
    if route and route.get("coordinates"):
        folium.PolyLine(route["coordinates"],color="#25C9B5",weight=5,opacity=.9,tooltip="OSRM route estimate").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m

def render_browser_alert(message, title="KAVACH alert", language="English"):
    msg=json.dumps(str(message))
    ttl=json.dumps(str(title))
    voice_lang=json.dumps("hi-IN" if str(language).lower().startswith("h") else "en-IN")
    components.html(f"""
    <div style="font-family:Arial;color:#eef7fa;background:#102b35;border:1px solid #25c9b5;border-radius:10px;padding:12px">
      <b style="color:#ffbf47">Browser alert demonstration</b>
      <p style="font-size:13px">Click a button to request browser permission, play a local siren tone, or speak the warning.</p>
      <button id="perm" style="padding:8px;margin:3px;border-radius:7px">Enable browser notifications</button>
      <button id="siren" style="padding:8px;margin:3px;border-radius:7px">Play siren</button>
      <button id="voice" style="padding:8px;margin:3px;border-radius:7px">Speak warning</button>
      <span id="status" style="font-size:12px;color:#8ce3d8"></span>
    </div>
    <script>
    const message={msg}, title={ttl}, voiceLang={voice_lang};
    document.getElementById('perm').onclick=async()=>{{
      if(!('Notification' in window)){{document.getElementById('status').textContent='Notifications unsupported';return;}}
      const p=await Notification.requestPermission();
      if(p==='granted'){{new Notification(title,{{body:message}});document.getElementById('status').textContent='Browser notification shown';}}
      else document.getElementById('status').textContent='Permission: '+p;
    }};
    document.getElementById('siren').onclick=()=>{{
      try{{
        const ctx=new (window.AudioContext||window.webkitAudioContext)();
        let count=0; const play=()=>{{
          if(count>=6){{ctx.close();return;}}
          const osc=ctx.createOscillator(), gain=ctx.createGain();
          osc.type='sawtooth'; osc.frequency.value=count%2?620:880;
          gain.gain.setValueAtTime(.0001,ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(.12,ctx.currentTime+.04);
          gain.gain.exponentialRampToValueAtTime(.0001,ctx.currentTime+.28);
          osc.connect(gain);gain.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+.3);
          count++;setTimeout(play,350);
        }};play();document.getElementById('status').textContent='Local siren demo playing';
      }}catch(e){{document.getElementById('status').textContent='Audio unavailable';}}
    }};
    document.getElementById('voice').onclick=()=>{{
      if(!('speechSynthesis' in window)){{document.getElementById('status').textContent='Speech not supported';return;}}
      const u=new SpeechSynthesisUtterance(message);u.lang=voiceLang;
      window.speechSynthesis.cancel();window.speechSynthesis.speak(u);
      document.getElementById('status').textContent='Spoken warning started';
    }};
    </script>""",height=150)

def render_command_centre(events, statuses, demo_on):
    st.subheader("National Command Centre")
    st.caption("India-focused multi-hazard view · source observations and simulated scenarios are visually separated.")
    if events.empty:
        st.warning("No event records are currently available. Check source connectivity or enable the labelled demo scenario.")
        return
    live=events[~events["simulated"].fillna(False)]
    sim=events[events["simulated"].fillna(False)]
    sos_rows=get_sos()
    active_sos=sum(1 for item in sos_rows if item.get("status") not in {"RESOLVED"})
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Events in view",len(events))
    c2.metric("Fire records",int((events.hazard=="Fire").sum()))
    c3.metric("Flood records",int((events.hazard=="Flood").sum()))
    c4.metric("Earthquake records",int((events.hazard=="Earthquake").sum()))
    c5.metric("Open test SOS",active_sos)
    if len(sim): st.info(f"{len(sim)} simulated scenario record(s) are included. They are not live observations.")
    with st.expander("Data-source connectivity", expanded=False):
        for source_name, source_status in statuses.items():
            (st.success if "Connected" in source_status or "Configured" in source_status else st.warning)(
                f"**{source_name}:** {source_status}"
            )
    left,right=st.columns([1.65,1])
    with left:
        st.markdown("#### Live hazard map")
        st_folium(build_map(events,sos_rows=sos_rows),width=None,height=540,returned_objects=[])
        st.caption("Switch between dark operations map and satellite imagery. Red pins are locally submitted prototype SOS reports; circles are incident markers, not official hazard boundaries.")
    with right:
        st.markdown("#### Threat-ranked incident queue")
        ranked=events.sort_values("threat_score",ascending=False).head(12)
        for _,r in ranked.iterrows():
            col=event_color(r)
            flag=" · SIMULATED" if bool(r.get("simulated",False)) else ""
            st.markdown(f"""<div class="k-card"><div class="k-eyebrow">{html.escape(str(r.hazard))}{flag}</div>
            <div style="font-weight:700;color:#F4F7FB">{html.escape(str(r.place))}</div>
            <div style="color:{col};font-weight:700">Threat score {int(r.threat_score)}/100 · {html.escape(str(r.severity))}</div>
            <div class="k-muted">{html.escape(str(r.observed))} · {html.escape(str(r.source))}</div></div>""",unsafe_allow_html=True)
    st.markdown("#### Incident register")
    hazards=st.multiselect("Filter hazards",["Fire","Flood","Earthquake"],default=["Fire","Flood","Earthquake"],key="cc_hazards")
    source_type=st.radio("Records",["All records","Live/source records only","Simulated only"],horizontal=True,key="cc_source_type")
    view=events[events.hazard.isin(hazards)].copy()
    if source_type=="Live/source records only": view=view[~view.simulated.fillna(False)]
    elif source_type=="Simulated only": view=view[view.simulated.fillna(False)]
    cols=["hazard","place","observed","severity","threat_score","source","simulated"]
    st.dataframe(view[cols].rename(columns={"hazard":"Hazard","place":"Incident","observed":"Observed","severity":"Severity","threat_score":"Threat / 100","source":"Source","simulated":"Simulated"}),
        use_container_width=True,hide_index=True)
    if not view.empty:
        options=view.index.tolist()
        idx=st.selectbox("Inspect incident",options,format_func=lambda i:f"{view.loc[i,'hazard']} · {view.loc[i,'place']}",key="cc_inspect")
        r=view.loc[idx]
        a,b,c=st.columns(3)
        a.metric("Latitude",f"{float(r.latitude):.4f}")
        b.metric("Longitude",f"{float(r.longitude):.4f}")
        c.metric("Threat score",f"{int(r.threat_score)}/100")
        st.write(f"**Details:** {r.detail}")
        if r.url: st.link_button("Open original source",r.url)
        st.caption(f"Prototype danger radius: {r.danger_radius_km} km · warning radius: {r.warning_radius_km} km. These are heuristic demo radii, not official evacuation perimeters.")
    if not events.empty:
        chart=events.groupby("hazard").size().reset_index(name="records")
        fig = px.bar(chart, x="hazard", y="records", color="hazard", title="Records by hazard",
                     color_discrete_map={"Fire": PALETTE["red"], "Flood": PALETTE["blue"], "Earthquake": PALETTE["gold"]})
        st.plotly_chart(_style_plotly(fig), use_container_width=True)

def render_alert_centre(events):
    st.subheader("Alert Centre · Geo-fenced notifications")
    st.warning("Prototype alert workflow. Browser alerts work only while this page is open and after user permission. SMS requires Twilio credentials. Cell Broadcast is a planned government-authorised integration.")
    if events.empty:
        st.info("No incident records to assess. Enable the demo scenario or refresh feeds.")
        return
    rows=[]
    for _,r in events.iterrows():
        pr=alert_priority(r.to_dict())
        rows.append({"Priority":pr,"Hazard":r.hazard,"Incident":r.place,"Threat":r.threat_score,
                     "Source":r.source,"Simulated":bool(r.simulated),"Event ID":r.id})
    df=pd.DataFrame(rows).sort_values("Threat",ascending=False)
    st.dataframe(df,use_container_width=True,hide_index=True)
    st.markdown("#### Test a person against a danger zone")
    incident_idx=st.selectbox("Choose incident",events.index.tolist(),format_func=lambda i:f"{events.loc[i,'hazard']} · {events.loc[i,'place']}",key="alert_incident")
    event=events.loc[incident_idx].to_dict()
    default_lat=float(event["latitude"])+0.0675
    default_lon=float(event["longitude"])
    with st.form("geo_test_form"):
        p1,p2=st.columns(2)
        lat=p1.number_input("Person latitude",value=default_lat,format="%.6f")
        lon=p2.number_input("Person longitude",value=default_lon,format="%.6f")
        language=st.selectbox("Alert language",["English","Hindi"])
        submit=st.form_submit_button("Check geo-fence status")
    if submit:
        status,distance=assess_person(event,lat,lon)
        message=make_message(event,language,status,distance)
        st.session_state["last_alert"]={"message":message,"status":status,"event":event,"distance":distance,"lat":lat,"lon":lon,"language":language}
    last=st.session_state.get("last_alert")
    if last:
        status=last["status"]
        if status=="DANGER": st.error(f"DEMO STATUS: DANGER · {last['distance']:.1f} km from incident")
        elif status=="WARNING": st.warning(f"DEMO STATUS: WARNING · {last['distance']:.1f} km from incident")
        else: st.success(f"DEMO STATUS: SAFE · {last['distance']:.1f} km from incident")
        st.code(last["message"])
        render_browser_alert(last["message"], language=last["language"])
        if st.button("Log this alert in local history"):
            log_alert(last["event"]["id"],status,last["message"],"Browser demo","Generated in active session")
            st.success("Alert logged locally.")
        phone=st.text_input("Recipient phone number in international format (optional)",placeholder="+91XXXXXXXXXX",key="alert_phone")
        if st.button("Send SMS via configured Twilio account"):
            ok,info=send_twilio_sms(phone,last["message"])
            log_alert(last["event"]["id"],status,last["message"],"Twilio SMS",info)
            (st.success if ok else st.error)(info)
    st.markdown("#### One-click zone alert preview")
    selected=events.loc[incident_idx]
    st.caption(f"Would target registered test locations within {selected.warning_radius_km} km. No mass broadcast is performed.")
    people=get_people()
    if people:
        out=[]
        for p in people:
            stat,dist=assess_person(selected.to_dict(),p["latitude"],p["longitude"])
            out.append({"Name":p["name"],"Status":stat,"Distance km":round(dist,2),"Language":p["language"],"Phone saved":bool(p["phone"])})
        st.dataframe(pd.DataFrame(out),use_container_width=True,hide_index=True)
        eligible=[p for p in people if assess_person(selected.to_dict(),p["latitude"],p["longitude"])[0] in {"DANGER","WARNING"} and p.get("phone")]
        st.caption(f"{len(eligible)} registered test location(s) have a saved phone number inside the warning zone.")
        confirm_zone=st.checkbox("I confirm these are consenting test recipients, not an emergency mass broadcast.",key="zone_sms_confirm")
        if st.button("Send geo-fenced test SMS to eligible registered people",disabled=not eligible or not confirm_zone):
            sent=0
            for p in eligible:
                stat,dist=assess_person(selected.to_dict(),p["latitude"],p["longitude"])
                msg=make_message(selected.to_dict(),p["language"],stat,dist)
                ok,info=send_twilio_sms(p["phone"],msg)
                log_alert(selected["id"],stat,msg,"Twilio geo-fenced test SMS",info)
                sent += int(ok)
            st.info(f"Twilio accepted {sent} of {len(eligible)} SMS request(s). Check individual results in local alert history; carrier delivery is not guaranteed.")
    else: st.info("No registered test people yet. Add test locations in the Citizen Safety page.")

def render_citizen(events):
    st.subheader("Citizen Safety · No app installation required")
    st.caption("This is a browser-based demonstration. Location is entered by the user; no location is collected in the background.")
    if events.empty:
        st.warning("No incident data available.")
        return
    incident_idx=st.selectbox("Select nearby incident",events.index.tolist(),format_func=lambda i:f"{events.loc[i,'hazard']} · {events.loc[i,'place']}",key="citizen_incident")
    ev=events.loc[incident_idx].to_dict()
    st.markdown("#### Check your location")
    with st.form("citizen_location"):
        n=st.text_input("Your name (optional)")
        phone=st.text_input("Phone (optional; stored locally only)")
        c1,c2=st.columns(2)
        lat=c1.number_input("Latitude",value=23.2599,format="%.6f")
        lon=c2.number_input("Longitude",value=77.4126,format="%.6f")
        lang=st.selectbox("Preferred alert language",["English","Hindi"])
        save=st.form_submit_button("Check safety and register test location")
    if save:
        status,distance=assess_person(ev,lat,lon)
        msg=make_message(ev,lang,status,distance)
        st.session_state["citizen_result"]={"status":status,"distance":distance,"message":msg,"lat":lat,"lon":lon,"language":lang,"name":n.strip()}
        if n.strip():
            add_person(n.strip(),phone.strip(),lat,lon,lang)
    res=st.session_state.get("citizen_result")
    if res:
        if res["status"]=="DANGER": st.error(f"YOUR DEMO STATUS: DANGER · {res['distance']:.1f} km from selected event")
        elif res["status"]=="WARNING": st.warning(f"YOUR DEMO STATUS: WARNING · {res['distance']:.1f} km from selected event")
        else: st.success(f"YOUR DEMO STATUS: SAFE · {res['distance']:.1f} km from selected event")
        st.code(res["message"])
        render_browser_alert(res["message"], language=res.get("language", "English"))
        st.markdown("#### Find nearby safe help")
        st.caption("Looks up mapped facilities and filters out those inside the selected prototype danger circle. Verify facility status and route independently.")
        if st.button("Find nearest mapped help outside the danger zone", key="citizen_find_help"):
            with st.spinner("Searching OpenStreetMap facilities..."):
                facilities, lookup_status = find_nearby_help(res["lat"], res["lon"], 25000)
            safe_facilities=[]
            for facility in facilities:
                distance_from_hazard=haversine_km(ev["latitude"],ev["longitude"],facility["latitude"],facility["longitude"])
                if distance_from_hazard > float(ev.get("danger_radius_km",5)):
                    facility["distance_from_person_km"]=haversine_km(res["lat"],res["lon"],facility["latitude"],facility["longitude"])
                    facility["distance_from_hazard_km"]=distance_from_hazard
                    safe_facilities.append(facility)
            st.session_state["citizen_safe_facilities"]=safe_facilities
            st.session_state["citizen_help_status"]=lookup_status
        if "citizen_help_status" in st.session_state:
            st.caption(st.session_state["citizen_help_status"])
            safe_facilities=st.session_state.get("citizen_safe_facilities",[])
            if safe_facilities:
                pick=st.selectbox("Choose a mapped facility outside the prototype danger zone",range(len(safe_facilities)),
                    format_func=lambda i:f"{safe_facilities[i]['name']} · {safe_facilities[i]['type']} · {safe_facilities[i]['distance_from_person_km']:.1f} km away",
                    key="citizen_help_pick")
                if st.button("Calculate route to selected help"):
                    facility=safe_facilities[pick]
                    route,route_status=get_osrm_route(res["lat"],res["lon"],facility["latitude"],facility["longitude"])
                    if route:
                        st.session_state["citizen_help_route"]=route
                        st.success(f"Route estimate: {route['distance_km']:.1f} km · {route['duration_min']:.0f} minutes. Not a live-traffic ETA.")
                    else:
                        st.warning(route_status)
                if st.session_state.get("citizen_help_route"):
                    st_folium(build_map(pd.DataFrame(),route=st.session_state["citizen_help_route"],person=(res["lat"],res["lon"])),height=350)
            else:
                st.info("No mapped facility outside the prototype danger zone was returned. Do not infer that no safe help exists.")
        st.markdown("#### Send an SOS to the Command Centre")
        with st.form("citizen_sos"):
            sos_name=st.text_input("Name",value=res.get("name", ""))
            sos_phone=st.text_input("Contact number (optional)")
            sos_msg=st.text_area("What help do you need?",value="I need assistance. Please contact me.")
            confirm=st.checkbox("I understand this sends a test SOS to this KAVACH prototype, not to emergency services.")
            submit=st.form_submit_button("Submit SOS")
        if submit:
            if confirm:
                sid=add_sos(sos_name,sos_phone,res["lat"],res["lon"],sos_msg,simulated=bool(ev.get("simulated",False)))
                st.success(f"Test SOS #{sid} saved to the local Command Centre.")
            else: st.error("Please confirm this is a prototype SOS.")
    st.info("For a real emergency in India, call 112 (or the relevant official emergency number). KAVACH does not contact emergency services.")

def render_rescue(events):
    st.subheader("Rescue & Help · Facility lookup and route estimate")
    st.caption("Uses OpenStreetMap community data and the public OSRM demo router. Verify every facility and route before relying on it.")
    with st.form("rescue_form"):
        c1,c2=st.columns(2)
        lat=c1.number_input("Incident / person latitude",value=23.2599,format="%.6f")
        lon=c2.number_input("Incident / person longitude",value=77.4126,format="%.6f")
        radius=st.selectbox("Search radius",["5 km","10 km","15 km"],index=2)
        go=st.form_submit_button("Find nearby hospitals, fire stations, police and shelters")
    if go:
        with st.spinner("Searching OpenStreetMap..."):
            facilities,status=find_nearby_help(lat,lon,int(radius.split()[0])*1000)
        st.session_state["facilities"]=facilities
        st.session_state["facility_status"]=status
        st.session_state["rescue_origin"]=(lat,lon)
    if "facility_status" in st.session_state:
        st.caption(st.session_state["facility_status"])
        facilities=st.session_state.get("facilities",[])
        if facilities:
            df=pd.DataFrame(facilities)
            st.dataframe(df[["name","type","distance_km","latitude","longitude","address"]].rename(columns={"name":"Facility","type":"Type","distance_km":"Distance km"}),
                use_container_width=True,hide_index=True)
            choice=st.selectbox("Choose a facility for route estimate",range(len(facilities)),format_func=lambda i:f"{facilities[i]['name']} · {facilities[i]['type']} · {facilities[i]['distance_km']:.1f} km")
            if st.button("Calculate driving route estimate"):
                origin=st.session_state["rescue_origin"]
                with st.spinner("Requesting OSRM route..."):
                    route,msg=get_osrm_route(origin[0],origin[1],facilities[choice]["latitude"],facilities[choice]["longitude"])
                if route:
                    st.session_state["rescue_route"]=route
                    st.success(f"Estimated route: {route['distance_km']:.1f} km · {route['duration_min']:.0f} min (not a live traffic ETA)")
                else: st.error(msg)
            if st.session_state.get("rescue_route"):
                route=st.session_state["rescue_route"]
                st_folium(build_map(pd.DataFrame(),route=route,person=st.session_state.get("rescue_origin")),height=400)
        else: st.warning("No facilities returned. Try a larger radius or check the Overpass endpoint.")
    st.markdown("#### Register a test location")
    with st.form("register_person"):
        name=st.text_input("Name")
        phone=st.text_input("Phone (optional)")
        a,b=st.columns(2)
        lat2=a.number_input("Latitude ",value=23.2599,format="%.6f")
        lon2=b.number_input("Longitude ",value=77.4126,format="%.6f")
        language=st.selectbox("Language",["English","Hindi"])
        reg=st.form_submit_button("Register test location")
    if reg and name.strip():
        add_person(name.strip(),phone.strip(),lat2,lon2,language)
        st.success("Test location registered locally.")

def render_sos_console():
    st.subheader("SOS Console · Command Centre")
    reports=get_sos()
    if not reports:
        st.info("No SOS reports submitted in this local prototype.")
        return
    st.dataframe(pd.DataFrame(reports),use_container_width=True,hide_index=True)
    ids=[x["id"] for x in reports]
    selected=st.selectbox("Select SOS report",ids,format_func=lambda i:f"SOS #{i}")
    status=st.selectbox("Update status",["NEW","ACKNOWLEDGED","IN_PROGRESS","RESOLVED"])
    if st.button("Update SOS status"):
        update_sos_status(selected,status)
        st.success(f"SOS #{selected} updated to {status}.")
        st.rerun()

def render_data_notes(statuses):
    st.subheader("Data Sources, Methodology & Transparency")
    st.markdown("### Live/source feeds")
    for name,status in statuses.items():
        if "Connected" in status or "Configured" in status:
            st.success(f"**{name}:** {status}")
        else:
            st.warning(f"**{name}:** {status}")
    st.markdown("""
    **Fire — NASA FIRMS:** satellite thermal anomalies/hotspots. A hotspot is not automatically a confirmed forest fire. The live feed requires a free FIRMS MAP_KEY.

    **Earthquakes — USGS:** global GeoJSON filtered to India's approximate bounding box. Magnitude is not local shaking intensity. For operational India-first use, integrate an authorised National Center for Seismology feed.

    **Floods — NASA EONET / GDACS:** event-catalogue records only. They do not provide flood depth, water level or a validated inundation polygon. Sentinel-1 SAR / Google Earth Engine flood change detection is a next-phase integration, not live in this version.

    **Population:** the Bhopal demo scenario uses the population figure stated in the pitch deck and is simulated. For live events, an adjustable density-based circle estimate may be used; it is a rough model, not a WorldPop/GHSL raster overlay. WorldPop/GHSL integration is next phase.

    **Danger and warning radii / threat score:** heuristic prototype calculations for demonstration and prioritisation. They are not official hazard perimeters, forecasts or evacuation orders.

    **Rescue facilities and routing:** OpenStreetMap and OSRM public community services. Data may be incomplete; route duration is not a live-traffic ETA.

    **Alerts:** browser notification, local siren tone and browser speech are interactive demonstrations while the page is open. They are not background Web Push, cell broadcast or official emergency warnings. Optional Twilio SMS requires valid credentials, sender setup, and any trial recipient verification.

    **SOS:** saved in the local SQLite database and visible in this app's Command Centre only. It does not dispatch responders.

    **Cell Broadcast / NDMA SACHET:** planned authorised integration only.
    """)
    st.markdown("### Planned / not live in this build")
    for item in ["Sentinel-1 flood mapping and Earth Engine processing","WorldPop / GHSL population raster overlay","Official NCS India feed (requires authorised feed endpoint)","Government-authorised NDMA SACHET / Cell Broadcast","Production push notifications and mobile client","Operational emergency-service dispatch and responder availability"]:
        st.markdown(f"- {item}")

def render_test_page(events):
    st.subheader("Prototype Validation")
    st.caption("Run deterministic unit tests on the geo-fence engine. These tests validate code behaviour, not real-world hazard accuracy.")
    from .core import geofence_status, haversine_km, cluster_fire_hotspots
    test_points=1080
    passed=0
    for i in range(test_points):
        # Test each point at a known distance class from a fixed centre.
        lat=23.2599 + (i % 36)*0.0001
        lon=77.4126 + ((i // 36) % 30)*0.0001
        status,_=geofence_status(lat,lon,23.2599,77.4126,21,35)
        if status=="DANGER": passed+=1
    st.metric("Deterministic geofence checks passed",f"{passed}/{test_points}")
    st.caption("Synthetic points are intentionally generated inside the 21 km demo danger radius. This is a code self-check, not a field validation or the same independent test result unless separately reproduced.")
    if st.button("Run hotspot clustering smoke test"):
        sample=pd.DataFrame([
            {"latitude":23.25,"longitude":77.41,"frp":100,"confidence":"h","observed":"test"},
            {"latitude":23.251,"longitude":77.411,"frp":90,"confidence":"h","observed":"test"},
            {"latitude":23.40,"longitude":77.60,"frp":20,"confidence":"n","observed":"test"}
        ])
        clusters=cluster_fire_hotspots(sample,8)
        st.write(clusters)
        st.success(f"Clustering test produced {len(clusters)} clusters from 3 synthetic hotspots.")
    logs=get_alert_log()
    if logs:
        st.markdown("#### Local alert history")
        st.dataframe(pd.DataFrame(logs),use_container_width=True,hide_index=True)


def render_satellite_data_lab():
    """CSV upload + exploration module integrated into the KAVACH Streamlit app."""
    from .data_lab import read_csv_upload, find_column, valid_coordinate_frame

    st.subheader("Satellite Data Lab")
    st.caption("Upload satellite, weather, seismic or field-survey CSV data to inspect, filter, chart and map it alongside KAVACH's live disaster feeds.")
    st.info("CSV uploads are analysed in this browser session. They are not automatically treated as verified live incidents or sent as emergency alerts.")

    uploaded = st.file_uploader("Upload a CSV dataset", type=["csv"], key="kavach_satellite_csv")
    if uploaded is None:
        st.markdown("#### What your CSV can contain")
        st.markdown("- **date / observed:** observation date or timestamp\n- **hazard / disaster_type:** Fire, Flood or Earthquake\n- **latitude / longitude:** coordinates for map plotting\n- **severity / magnitude / frp:** intensity or measurement fields\n- **population / people_exposed:** exposure estimate, if available")
        st.caption("You can still explore a CSV without these optional columns. The dashboard will show which analyses are possible.")
        sample_csv = ("date,hazard,latitude,longitude,severity,intensity,people_exposed\n"
                      "2026-11-18,Fire,23.2599,77.4126,High,510,12000\n"
                      "2026-11-19,Flood,25.5941,85.1376,Medium,2.4,8500\n"
                      "2026-11-20,Earthquake,28.6139,77.2090,Low,3.8,1500\n")
        st.download_button("Download sample CSV template", data=sample_csv,
                           file_name="kavach_sample_satellite_data.csv", mime="text/csv")
        st.caption("The sample rows are fictional examples for learning the upload format, not live disaster reports.")
        if st.session_state.get("kavach_csv_name"):
            st.success(f"Previously loaded in this session: {st.session_state['kavach_csv_name']}")
        return

    try:
        data = read_csv_upload(uploaded)
    except Exception as exc:
        st.error(f"Could not read this CSV: {type(exc).__name__}: {exc}")
        return
    if data.empty:
        st.warning("This CSV has headers but no data rows.")
        return

    st.session_state["kavach_csv_name"] = uploaded.name
    st.session_state["kavach_csv_data"] = data
    st.markdown("#### Dataset overview")
    a,b,c,d = st.columns(4)
    a.metric("Total records", f"{len(data):,}")
    b.metric("Columns", len(data.columns))
    b2 = int(data.isna().sum().sum())
    c.metric("Missing cells", f"{b2:,}")
    d.metric("Duplicate rows", f"{int(data.duplicated().sum()):,}")
    st.caption(f"File: {uploaded.name} · {len(data):,} rows × {len(data.columns):,} columns")

    with st.expander("Inspect columns and data types", expanded=False):
        schema = pd.DataFrame({"Column": data.columns.astype(str), "Data type": data.dtypes.astype(str).values,
                               "Missing values": data.isna().sum().values})
        st.dataframe(schema, use_container_width=True, hide_index=True)
        st.write("Available columns:", data.columns.tolist())

    columns = list(data.columns)
    date_guess = find_column(columns, ["date", "datetime", "timestamp", "observed", "acq_date", "time"])
    hazard_guess = find_column(columns, ["hazard", "disaster", "disaster_type", "event_type", "category"])
    lat_guess = find_column(columns, ["latitude", "lat", "y"])
    lon_guess = find_column(columns, ["longitude", "lon", "lng", "long", "x"])
    severity_guess = find_column(columns, ["severity", "intensity", "magnitude", "frp", "confidence"])

    st.markdown("#### Filters and column mapping")
    f1,f2 = st.columns(2)
    date_col = f1.selectbox("Date / time column", ["— None —"] + columns,
                            index=(columns.index(date_guess)+1 if date_guess in columns else 0), key="csv_date_col")
    hazard_col = f2.selectbox("Hazard / category column", ["— None —"] + columns,
                              index=(columns.index(hazard_guess)+1 if hazard_guess in columns else 0), key="csv_hazard_col")

    filtered = data.copy()
    parsed_dates = None
    if date_col != "— None —":
        parsed_dates = pd.to_datetime(data[date_col], errors="coerce", utc=True)
        valid_dates = parsed_dates.dropna()
        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()
            date_range = st.date_input("Filter observation dates", value=(min_date, max_date),
                                       min_value=min_date, max_value=max_date, key="csv_date_range")
            if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
                start, end = pd.Timestamp(date_range[0], tz="UTC"), pd.Timestamp(date_range[1], tz="UTC") + pd.Timedelta(days=1)
                filtered = filtered.loc[(parsed_dates >= start) & (parsed_dates < end)].copy()
            filtered["_KAVACH parsed date"] = parsed_dates.loc[filtered.index]
        else:
            st.warning(f"Column '{date_col}' could not be parsed as dates. Date filtering and timeline chart are unavailable.")
    else:
        st.warning("No date column selected. Date filtering and monthly timeline chart are unavailable.")

    if hazard_col != "— None —":
        values = sorted(filtered[hazard_col].dropna().astype(str).unique().tolist())
        if values:
            selected_hazards = st.multiselect("Filter categories", values, default=values, key="csv_hazard_filter")
            filtered = filtered[filtered[hazard_col].astype(str).isin(selected_hazards)].copy()

    st.markdown("#### Dataset analytics")
    x,y,z = st.columns(3)
    x.metric("Records after filters", f"{len(filtered):,}")
    y.metric("Rows removed", f"{len(data)-len(filtered):,}")
    z.metric("Unique categories", filtered[hazard_col].nunique() if hazard_col != "— None —" else "—")

    if date_col != "— None —" and "_KAVACH parsed date" in filtered.columns:
        timeline = (filtered.dropna(subset=["_KAVACH parsed date"])
                    .assign(Month=lambda x: x["_KAVACH parsed date"].dt.strftime("%Y-%m"))
                    .groupby("Month").size().reset_index(name="Records"))
        if not timeline.empty:
            fig = px.bar(timeline, x="Month", y="Records", title="Records by month",
                         color_discrete_sequence=[PALETTE["gold"]])
            st.plotly_chart(_style_plotly(fig), use_container_width=True)

    if hazard_col != "— None —" and not filtered.empty:
        counts = filtered[hazard_col].astype(str).value_counts().rename_axis("Category").reset_index(name="Records")
        fig = px.bar(counts, x="Category", y="Records", color="Category",
                     title="Records by hazard / category",
                     color_discrete_sequence=[PALETTE["gold"], PALETTE["cyan"], PALETTE["red"], PALETTE["blue"]])
        st.plotly_chart(_style_plotly(fig), use_container_width=True)

    st.markdown("#### Geographic view")
    g1,g2 = st.columns(2)
    lat_col = g1.selectbox("Latitude column", ["— None —"] + columns,
                           index=(columns.index(lat_guess)+1 if lat_guess in columns else 0), key="csv_lat_col")
    lon_col = g2.selectbox("Longitude column", ["— None —"] + columns,
                           index=(columns.index(lon_guess)+1 if lon_guess in columns else 0), key="csv_lon_col")
    if lat_col != "— None —" and lon_col != "— None —":
        geo = valid_coordinate_frame(filtered, lat_col, lon_col)
        if not geo.empty:
            st.metric("Rows with valid coordinates", f"{len(geo):,}")
            map_df = geo.rename(columns={"_latitude":"latitude", "_longitude":"longitude"})
            if hazard_col != "— None —":
                map_df["_map_label"] = map_df[hazard_col].astype(str)
                fig = px.scatter_mapbox(map_df, lat="latitude", lon="longitude", color="_map_label",
                                        hover_name="_map_label", zoom=3.5, height=460,
                                        title="Uploaded dataset locations", mapbox_style="carto-darkmatter")
            else:
                fig = px.scatter_mapbox(map_df, lat="latitude", lon="longitude", zoom=3.5,
                                        height=460, title="Uploaded dataset locations",
                                        mapbox_style="carto-darkmatter")
            st.plotly_chart(_style_plotly(fig, height=460), use_container_width=True)
        else:
            st.warning("No valid coordinate pairs were found in the filtered rows.")
    else:
        st.caption("Select latitude and longitude columns to display a geographic plot.")

    st.markdown("#### Dataset table")
    display_data = filtered.drop(columns=["_KAVACH parsed date"], errors="ignore")
    st.dataframe(display_data, use_container_width=True, hide_index=True)
    csv_bytes = display_data.to_csv(index=False).encode("utf-8-sig")
    st.download_button("Download filtered CSV", data=csv_bytes,
                       file_name=f"kavach_filtered_{uploaded.name}", mime="text/csv")

    if severity_guess and severity_guess in filtered.columns:
        st.caption(f"Detected a possible intensity field: **{severity_guess}**. Its meaning depends on the source dataset (for example, magnitude and FRP are not interchangeable).")
    st.caption("Data provenance reminder: uploaded rows are user-provided and are not verified by KAVACH. Do not use them to issue real-world evacuation instructions.")
