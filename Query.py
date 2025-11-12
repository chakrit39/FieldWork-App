# optimized_app.py
import os
import time
import math
import json
import uuid
import requests
import datetime

import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from shapely.geometry import shape, Point, LineString
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
import gspread

# Optional: cookie manager (kept but fallback to uuid session id)
from streamlit_cookies_manager import EncryptedCookieManager

# ------------------------------
# Basic Streamlit config (call early)
# ------------------------------
st.set_page_config(page_title="Query", layout="wide")

# ------------------------------
# Font setup (only once)
# ------------------------------
FONT_PATH = "./tahoma.ttf"
if os.path.exists(FONT_PATH):
    try:
        fm.fontManager.addfont(FONT_PATH)
        prop = fm.FontProperties(fname=FONT_PATH)
        plt.rcParams['font.family'] = prop.get_name()
        plt.rcParams['font.sans-serif'] = [prop.get_name()]
    except Exception:
        pass  # don't crash if font registration fails

# ------------------------------
# Cookie / session id helper (safer)
# ------------------------------
# Try EncryptedCookieManager, but fallback to a uuid stored in session_state
cookie_manager = None
try:
    cookie_manager = EncryptedCookieManager(prefix="my_app", password="my_secrets_key")
    if cookie_manager.ready():
        session_cookie_id = cookie_manager.get("session_id") or None
        if session_cookie_id is None:
            session_cookie_id = str(uuid.uuid4())
            cookie_manager.set("session_id", session_cookie_id)
            cookie_manager.save()
    else:
        # Not ready yet -> stop (streamlit cookie manager pattern)
        st.stop()
except Exception:
    # fallback: use server-side session id
    session_cookie_id = st.session_state.get("_session_id", None)
    if session_cookie_id is None:
        session_cookie_id = str(uuid.uuid4())
        st.session_state["_session_id"] = session_cookie_id

# ------------------------------
# Utility: session-state containers
# ------------------------------
# Ensure container keys exist and are lightweight
if "Data" not in st.session_state:
    st.session_state["Data"] = {}
if "Search" not in st.session_state:
    st.session_state["Search"] = False
if "verity" not in st.session_state:
    st.session_state["verity"] = False
if "cookies" not in st.session_state:
    st.session_state["cookies"] = {}

# store cookie-specific dict server-side (avoids direct low-level api usage)
if session_cookie_id not in st.session_state["cookies"]:
    st.session_state["cookies"][session_cookie_id] = {}

# ------------------------------
# Google service: cached resource
# ------------------------------
SCOPE = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]

@st.cache_resource
def get_service_and_sheet(secrets_dict):
    """
    Return: (creds, gspread_client, drive_service, gspread_spreadsheet, worksheet)
    Cached as resource to avoid reauth each rerun.
    """
    creds = ServiceAccountCredentials.from_json_keyfile_dict(secrets_dict, SCOPE)
    gc = gspread.authorize(creds)
    drive_service = build("drive", "v3", credentials=creds)
    sh = gc.open('DOLCAD')
    wks = sh.worksheet('Raw')
    return creds, gc, drive_service, sh, wks

# ------------------------------
# Lightweight cached read helpers
# ------------------------------
@st.cache_data(ttl=3600)
def load_utm_map_csv(path="./UTMMAP4.csv"):
    return pd.read_csv(path, header=0, dtype={'UTMMAP4': str})

@st.cache_data(ttl=300)
def load_sheet_as_df(wks):
    """Get Google sheet content as DataFrame. Cached for short ttl."""
    records = wks.get_all_records()
    return pd.DataFrame(records)

@st.cache_data(ttl=3600)
def fetch_geojson_pair(poly_url, point_url):
    """Fetch geojsons and return (poly_json, point_json, geopandas_points)"""
    # Use requests with reasonable timeout
    r1 = requests.get(poly_url, timeout=10)
    r1.raise_for_status()
    poly_json = r1.json()

    r2 = requests.get(point_url, timeout=10)
    r2.raise_for_status()
    point_json = r2.json()

    # geopandas read_file accepts url; slice last row as original
    gdf_points = gpd.read_file(point_url)[:-1] if point_json.get("features") else gpd.GeoDataFrame()
    return poly_json, point_json, gdf_points

# ------------------------------
# Lightweight cookie UTM setter/getter
# ------------------------------
def set_utm_name_for_session(session_id, utm_name):
    st.session_state["cookies"].setdefault(session_id, {})
    st.session_state["cookies"][session_id]["UTM_Name"] = utm_name

def get_utm_name_for_session(session_id):
    return st.session_state["cookies"].get(session_id, {}).get("UTM_Name", "")

# ------------------------------
# Login UI (simple modal-like)
# ------------------------------
if not st.session_state["verity"]:
    # Simple login form
    with st.form("login"):
        st.markdown("#### โปรดใส่รหัส")
        password = st.text_input("รหัสผ่าน", "", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if password == st.secrets["PASSWD"]:
                st.session_state["verity"] = True
            else:
                st.error("รหัสผ่านไม่ถูกต้อง")

# ------------------------------
# Main app after verification
# ------------------------------
if st.session_state["verity"]:
    # get google service + sheet
    creds, gc, drive_service, sh, wks = get_service_and_sheet(st.secrets["dol-mtd5-fieldwork"])
    df = load_sheet_as_df(wks)
    sc = load_utm_map_csv()

    # --- UI: inputs in a single row for compactness
    col_1, col_2, col_3, col_4, col_5 , col_6 = st.columns([0.2,0.13,0.2,0.2,0.13,0.15])
    UTMMAP1 = col_1.text_input("UTMMAP1","")
    UTMMAP2 = col_2.selectbox("UTMMAP2",["1","2","3","4"])
    UTMMAP3 = col_3.text_input("UTMMAP3","")
    Scale = col_4.selectbox("Scale", pd.unique(sc.SCALE))
    UTMMAP4 = col_5.selectbox("UTMMAP4", pd.unique(sc.UTMMAP4[sc.SCALE==Scale]))
    land_no = col_6.text_input("เลขที่ดิน","")

    # --------------------------------------------
    # Search handler (kept minimal)
    # --------------------------------------------
    if st.button("Search"):
        if UTMMAP1 and UTMMAP3 and land_no:
            UTM = f"{UTMMAP1} {UTMMAP2} {UTMMAP3}-{UTMMAP4}({Scale})_{land_no}"
            set_utm_name_for_session(session_cookie_id, UTM)

            row = df[df['Name']==UTM]
            if row.empty:
                st.warning("ไม่พบรูปแปลงที่ดิน")
                st.session_state["Search"] = False
            else:
                # get file ids
                try:
                    id_poly = row[row['Type']=='Polygon']['ID'].iloc[0]
                    id_point = row[row['Type']=='Point']['ID'].iloc[0]
                except Exception:
                    st.error("ข้อมูลใน sheet ไม่สมบูรณ์: ไม่มีทั้ง Polygon/Point ID")
                    st.session_state["Search"] = False
                else:
                    poly_url = f"https://drive.google.com/uc?id={id_poly}&export%3Fformat=geojson"
                    point_url = f"https://drive.google.com/uc?id={id_point}&export%3Fformat=geojson"

                    # fetch (cached)
                    try:
                        poly_json, point_json, gdf_points = fetch_geojson_pair(poly_url, point_url)
                    except Exception as e:
                        st.error(f"โหลดข้อมูลล้มเหลว: {e}")
                        st.session_state["Search"] = False
                    else:
                        # store in session cache for reuse in same session
                        st.session_state["Data"][UTM] = {
                            "poly_data": poly_json,
                            "point_data": point_json,
                            "data_point": gdf_points,
                        }
                        st.session_state["Search"] = True
        else:
            st.warning("โปรดกรอกข้อมูลให้ครบถ้วน")
            st.session_state["Search"] = False

    # --------------------------------------------
    # If previously loaded UTM in session, render results
    # --------------------------------------------
    UTM_saved = get_utm_name_for_session(session_cookie_id)
    if UTM_saved and UTM_saved in st.session_state["Data"]:
        poly_data = st.session_state["Data"][UTM_saved]["poly_data"]
        point_data = st.session_state["Data"][UTM_saved]["point_data"]
        data_point = st.session_state["Data"][UTM_saved]["data_point"]

        # prepare polygons & points
        polygons = [shape(feat["geometry"]) for feat in poly_data.get("features", [])]
        points_feats = point_data.get("features", []) if isinstance(point_data, dict) else []

        # heuristic scale based on polygon size (safe guard)
        sc_val = None
        if polygons:
            try:
                sc_val = max(1.0, polygons[0].length / 120.0)
            except Exception:
                sc_val = 1.0
        else:
            sc_val = 1.0

        # find candidate name column for points (once)
        name_col = None
        if points_feats:
            for k in points_feats[0]["properties"].keys():
                if any(word in k.lower() for word in ["name", "label", "id", "point"]):
                    name_col = k
                    break

        # --------- plotting (vectorized-ish) ----------
        fig, ax = plt.subplots(figsize=(10, 10))

        # Draw polygons (outline + fill)
        for poly in polygons:
            x, y = poly.exterior.xy
            ax.plot(x, y, linewidth=1)
            ax.fill(x, y, alpha=0.08, fc="lightblue")

            # compute all segments in one pass using coords array
            coords = list(poly.exterior.coords)
            coords_arr = np.array(coords)
            p1 = coords_arr[:-1]
            p2 = coords_arr[1:]
            # vector differences
            diffs = p2 - p1
            dists = np.hypot(diffs[:,0], diffs[:,1])
            # midpoints
            mids = (p1 + p2) / 2.0

            # angles (radians) and azimuths
            angles = np.degrees(np.arctan2(diffs[:,1], diffs[:,0]))
            # convert to plotting rotation
            # offset direction normal to segment
            normals = np.column_stack((np.cos(np.radians(angles + 90)), np.sin(np.radians(angles + 90))))
            offsets = normals * sc_val

            for i, (mx,my,dist,angle,off) in enumerate(zip(mids[:,0], mids[:,1], dists, angles, offsets)):
                ox, oy = off
                # check inside - if midpoint+offset is inside polygon, flip sign
                mid_pt = Point(mx + ox, my + oy)
                if mid_pt.within(poly):
                    ox, oy = -ox, -oy
                ax.text(mx + ox, my + oy, f"{dist:.3f} m",
                        fontsize=8, ha='center', va='center',
                        rotation=angle, rotation_mode='anchor')

        # Draw points with "smart" offset relative to polygon centroid
        centroids = [poly.centroid for poly in polygons] if polygons else []
        for i, feat in enumerate(points_feats):
            geom = shape(feat["geometry"])
            ax.plot(geom.x, geom.y, "ro", markersize=4)
            label = str(feat["properties"].get(name_col, f"P{i+1}")) if name_col else f"P{i+1}"

            # decide offset direction by vector from nearest polygon centroid
            ox, oy = 0.0, sc_val * 2.0
            if centroids:
                # choose centroid with smallest distance
                dists_to_centroids = [geom.distance(c) for c in centroids]
                c = centroids[int(np.argmin(dists_to_centroids))]
                dx, dy = geom.x - c.x, geom.y - c.y
                if dx == 0 and dy == 0:
                    ox, oy = 0, sc_val * 2.0
                else:
                    # normalize and multiply
                    length = math.hypot(dx, dy)
                    ox, oy = (dx / length) * sc_val * 2.0, (dy / length) * sc_val * 2.0

            ax.text(geom.x + ox, geom.y + oy, label,
                    fontsize=9, color="red", ha="center", va="center")

        ax.set_title(f"\n{UTM_saved}  {poly_data['features'][0]['properties'].get('SURVEY_UNITNAME','')}\n")
        ax.axis("equal")
        st.pyplot(fig)

        # -------- table of points (compact) ----------
        if not data_point.empty:
            h = len(data_point)
            show_cols = [c for c in ['PCM_BNDNAME','PCM_NORTH','PCM_EAST'] if c in data_point.columns]
            st.dataframe(data=data_point[show_cols], width="stretch", height=35*(h+1))

            # point pair distance UI
            c01, c02, c03 = st.columns([0.35,0.35,0.3])
            Name_list = data_point["PCM_BNDNAME"].tolist()
            point1 = c01.selectbox("หมุดหลักเขต 1", Name_list, key="p1")
            point2 = c02.selectbox("หมุดหลักเขต 2", Name_list, key="p2")

            length = 0.0
            if point1 != point2:
                p1_geom = data_point.loc[data_point['PCM_BNDNAME']==point1,'geometry'].iloc[0]
                p2_geom = data_point.loc[data_point['PCM_BNDNAME']==point2,'geometry'].iloc[0]
                length = round(p1_geom.distance(p2_geom), 3)

            length_ = c03.selectbox("ระยะ", str(length))
            if length > 0:
                c1, c2 = st.columns([0.50,0.50])
                number = c1.number_input("ระยะที่วัดได้", value=0.0, step=0.001, format="%0.3f")
                if number != 0:
                    diff = abs(round(length - float(number), 3))
                    c2.text_input("ค่าต่าง", value=str(diff))
