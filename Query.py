import streamlit as st
import pandas as pd
import numpy as np
#from streamlit_folium import folium_static
import geopandas as gpd
from requests.auth import HTTPBasicAuth
import time
import datetime
import os
import gspread
from sqlalchemy import create_engine
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from PIL import Image
from pillow_heif import register_heif_opener
import json
import matplotlib.pyplot as plt
from shapely.geometry import shape, Point
import math
import requests
import matplotlib.font_manager as fm

st.set_page_config(page_title="Query")

font_path = "./tahoma.ttf"
fm.fontManager.addfont(font_path)
prop = fm.FontProperties(fname=font_path)
# Set Matplotlib's default font to the Thai font
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['font.sans-serif'] = [prop.get_name()] # Also set sans-serif if needed

# === Path ไปยังไฟล์ของคุณ ===
poly_url = "https://drive.google.com/uc?id=1T731fgDUaa-DcRHHirZiv165JMy2rIfg&export%3Fformat=geojson"
point_url = "https://drive.google.com/uc?id=1cHJhf_gicoUIekg1MqKk3WCDY65CmGGt&export%3Fformat=geojson"

# === โหลดไฟล์ ===
poly_data = requests.get(poly_url).json()
point_data = requests.get(point_url).json()

polygons = [shape(feat["geometry"]) for feat in poly_data["features"]]
points = [shape(feat["geometry"]) for feat in point_data["features"]]

sc = polygons[0].length/120

# === หาชื่อคอลัมน์ point ===
name_col = None
if len(point_data["features"]) > 0:
    for k in point_data["features"][0]["properties"].keys():
        if any(word in k.lower() for word in ["name", "label", "id", "point"]):
            name_col = k
            break

fig, ax = plt.subplots(figsize=(12, 10))

# === วาด polygon + label ระยะ ===
for poly in polygons:
    x, y = poly.exterior.xy
    ax.plot(x, y, color="black", linewidth=1)
    ax.fill(x, y, alpha=0.1, fc="lightblue")

    coords = list(poly.exterior.coords)
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        dist = Point(x1, y1).distance(Point(x2, y2))
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2

        # มุมทางคณิตศาสตร์
        angle_math = math.degrees(math.atan2(y2 - y1, x2 - x1))
        azimuth = (90 - angle_math) % 360
        
        if azimuth > 180 :
            angle_math = angle_math + 180
            
        # เวกเตอร์ตั้งฉาก
        nx = math.cos(math.radians(angle_math + 90))
        ny = math.sin(math.radians(angle_math + 90))

        # offset ออกนอก polygon
        offset = sc
        ox, oy = nx * offset, ny * offset
        mid_point = Point(mx + ox, my + oy)
        if mid_point.within(poly):
            ox, oy = -ox, -oy

        # วางข้อความระยะ (ไม่มี azimuth)
        ax.text(mx + ox, my + oy, f"{dist:.3f} m",
                fontsize=8, ha='center', va='center',
                rotation=angle_math, rotation_mode='anchor')

# === วาดจุด + ชื่อพร้อม offset ฉลาด ===
for i, feat in enumerate(point_data["features"]):
    geom = shape(feat["geometry"])
    ax.plot(geom.x, geom.y, "ro", markersize=5)

    label = str(feat["properties"].get(name_col, f"P{i+1}")) if name_col else f"P{i+1}"
    point = Point(geom.x, geom.y)
    offset_dist = sc*1.2  # ระยะ offset ออกนอก
    ox, oy = 0, offset_dist

    # หาทิศทางออกจาก polygon โดยใช้ centroid เป็นศูนย์กลาง
    for poly in polygons:
        cx, cy = poly.centroid.x, poly.centroid.y
        dx, dy = geom.x - cx, geom.y - cy
        length = math.hypot(dx, dy)
        if length != 0:
            if dx < 0:
                dx = -1
            else:
                dx = 1
            if dy < 0:
                dy = -1
            else:
                dy = 1        
            ox, oy = dx  * offset_dist, dy * offset_dist
            #ox, oy = (dx / length) * offset_dist, (dy / length) * offset_dist
    # วาด label offset ออกนอก polygon
    ax.text(geom.x + ox, geom.y + oy, label,
            fontsize=9, color="red", ha="center", va="center")

ax.set_title("Polygon + Points (EPSG:24047)\nDistances + Smart Point Label Offset (No Azimuth) ")
ax.axis("equal")
st.pyplot(fig)

"""
    --------------
"""

data_point = gpd.read_file(point_url)[['PCM_BNDNAME' , 'PCM_NORTH' , 'PCM_EAST']]
st.dataframe(data=data_point,use_container_width=True)
"""
    --------------
"""
c01, c02, c03 = st.columns([0.35,0.35,0.3])
Name_list = data_point["PCM_BNDNAME"].to_list()
point1 = c01.selectbox("หมุดหลักเขต 1",Name_list)
point2 = c02.selectbox("หมุดหลักเขต 2",Name_list)
