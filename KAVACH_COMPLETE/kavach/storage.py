from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent.parent / "kavach_data.sqlite3"

def connect():
    con=sqlite3.connect(DB_PATH,check_same_thread=False)
    con.row_factory=sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS sos_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, name TEXT, phone TEXT, latitude REAL NOT NULL,
            longitude REAL NOT NULL, message TEXT, status TEXT NOT NULL DEFAULT 'NEW',
            simulated INTEGER NOT NULL DEFAULT 0
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS registered_people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, phone TEXT, latitude REAL NOT NULL, longitude REAL NOT NULL,
            language TEXT DEFAULT 'English', created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS alert_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            event_id TEXT, priority TEXT, message TEXT, channel TEXT, result TEXT
        )""")

def add_sos(name, phone, lat, lon, message, simulated=False):
    with connect() as con:
        cur=con.execute("INSERT INTO sos_reports(created_at,name,phone,latitude,longitude,message,simulated) VALUES(?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(),name,phone,float(lat),float(lon),message,int(simulated)))
        return cur.lastrowid

def get_sos():
    with connect() as con:
        return [dict(x) for x in con.execute("SELECT * FROM sos_reports ORDER BY id DESC LIMIT 200").fetchall()]

def update_sos_status(report_id,status):
    with connect() as con:
        con.execute("UPDATE sos_reports SET status=? WHERE id=?",(status,int(report_id)))

def add_person(name,phone,lat,lon,language):
    with connect() as con:
        cur=con.execute("INSERT INTO registered_people(name,phone,latitude,longitude,language,created_at) VALUES(?,?,?,?,?,?)",
            (name,phone,float(lat),float(lon),language,datetime.now(timezone.utc).isoformat()))
        return cur.lastrowid

def get_people():
    with connect() as con:
        return [dict(x) for x in con.execute("SELECT * FROM registered_people ORDER BY id DESC").fetchall()]

def log_alert(event_id,priority,message,channel,result):
    with connect() as con:
        con.execute("INSERT INTO alert_log(created_at,event_id,priority,message,channel,result) VALUES(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(),event_id,priority,message,channel,result))

def get_alert_log():
    with connect() as con:
        return [dict(x) for x in con.execute("SELECT * FROM alert_log ORDER BY id DESC LIMIT 300").fetchall()]
