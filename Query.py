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
from streamlit_cookies_manager import EncryptedCookieManager

cookies = EncryptedCookieManager(prefix="my_app",password="my_secrets_key")
if not cookies.ready():
    st.stop()
cookies = cookies._cookie_manager["session_id"]

@st.cache_data()    
def get_cookies(cookies):
    if "cookies" not in st.session_state:
        st.session_state["cookies"] = {}
    if cookies not in st.session_state["cookies"]:
        st.session_state["cookies"][cookies] = {}
    return st.session_state["cookies"][cookies]

cookies_id = get_cookies(cookies)
st.session_state

if "Search" not in st.session_state:
    st.session_state["Search"] = False
    
if "Search_" not in st.session_state:
    st.session_state["Search_"] = False
    
if "Polygon" not in st.session_state:
    st.session_state["Polygon"] = False

if "verity" not in st.session_state:
    st.session_state["verity"] = False
    
scope = ['https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/spreadsheets',
        ]

@st.cache_resource
def get_service():
    #if "creds" not in globals() :
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["dol-mtd5-fieldwork"], scope)
    gc = gspread.authorize(creds)
    service = build("drive", "v3", credentials=creds)
    sh = gc.open('DOLCAD')
    wks = sh.worksheet('Raw')
    return creds,gc,service,sh,wks
    
@st.cache_data(ttl=3600)
def get_data(UTM_Name,poly_url,point_url):
    if "Data" not in st.session_state :
        st.session_state["Data"] = {}
    if UTM_Name not in st.session_state["Data"] :
        st.session_state["Data"][UTM_Name] = {}
    st.session_state["Data"][UTM_Name]["poly_data"] = requests.get(poly_url).json()
    st.session_state["Data"][UTM_Name]["point_data"] = requests.get(point_url).json()
    st.session_state["Data"][UTM_Name]["data_point"] = gpd.read_file(point_url)[:-1]
    return st.session_state["Data"][UTM_Name]["poly_data"],st.session_state["Data"][UTM_Name]["point_data"],st.session_state["Data"][UTM_Name]["data_point"]
    
@st.cache_data    
def get_List():
    df = pd.DataFrame(wks.get_all_records())
    sc = pd.read_csv('./UTMMAP4.csv',header=0,dtype={'UTMMAP4': str})
    return df,sc
    

    
@st.cache_data(ttl=3600)    
def get_UTM_Name(UTM):
    if "UTM_Name" not in st.session_state["cookies"][cookies] :
        st.session_state["cookies"][cookies]["UTM_Name"] = ""
    st.session_state["cookies"][cookies]["UTM_Name"] = UTM
    return st.session_state["cookies"][cookies]["UTM_Name"]
    
@st.dialog("รหัสผ่านไม่ถูกต้อง !!", width="small")
def pop_up():
    if st.button("ตกลง"):
        st.rerun()


if st.session_state["verity"] == False:
    placeholder = st.empty()
    with placeholder.form("login"):
        st.markdown("#### โปรดใส่รหัส")
        password = st.text_input("รหัสผ่าน","", type="password")
        verity = st.form_submit_button("Login")
        if verity:
            if password == st.secrets["PASSWD"]:
                st.session_state["verity"] = True
                placeholder.empty()
            else:
                pop_up()
                st.session_state["verity"] = False
        
creds,gc,service,sh,wks = get_service()
df,sc = get_List()  

if st.session_state["verity"]:
    st.set_page_config(page_title="Query")
    
    font_path = "./tahoma.ttf"
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    # Set Matplotlib's default font to the Thai font
    plt.rcParams['font.family'] = prop.get_name()
    plt.rcParams['font.sans-serif'] = [prop.get_name()] # Also set sans-serif if needed
    
    col_1, col_2, col_3, col_4, col_5 , col_6 = st.columns([0.2,0.13,0.2,0.2,0.13,0.15])
    UTMMAP1 = col_1.text_input("UTMMAP1","")
    UTMMAP2 = col_2.selectbox("UTMMAP2",["1", "2", "3", "4"],)
    UTMMAP3 = col_3.text_input("UTMMAP3","")
    Scale = col_4.selectbox("Scale",pd.unique(sc.SCALE),)
    UTMMAP4 = col_5.selectbox("UTMMAP4",pd.unique(sc.UTMMAP4[sc.SCALE==Scale]),)
    land_no = col_6.text_input("เลขที่ดิน","")
    
    if st.button("Search"):
        if UTMMAP1 != "" and UTMMAP3 != "" and land_no != "" :
                
            # === Path ไปยังไฟล์ของคุณ ===
            UTM = str(UTMMAP1) + " " + str(UTMMAP2) + " " + str(UTMMAP3) + "-" + str(UTMMAP4) + "(" + str(Scale) + ")_" + str(land_no)
            UTM_Name = get_UTM_Name(UTM)
            if UTM_Name != UTM:
                get_UTM_Name.clear()
                UTM_Name = get_UTM_Name(UTM)
            
            id = df[df['Name']==UTM]
            if len(id) == 0 :
                st.warning("ไม่พบรูปแปลงที่ดิน")
                st.session_state["Search"] = False
                st.session_state["Search_"] = False
            else:
                id_poly = id[id['Type']=='Polygon']['ID'].iloc[0]
                id_point = id[id['Type']=='Point']['ID'].iloc[0]
    
                poly_url = "https://drive.google.com/uc?id=" + id_poly + "&export%3Fformat=geojson"
                point_url = "https://drive.google.com/uc?id=" + id_point + "&export%3Fformat=geojson"
                poly_data,point_data,data_point = get_data(UTM_Name,poly_url,point_url)
                st.session_state["Search"] = True
                st.session_state["Search_"] = True
        else:
            st.warning("โปรดกรอกข้อมูลให้ครบถ้วน")
            st.session_state["Search"] = False
            st.session_state["Search_"] = False
    else:
        st.session_state["Search"] = False
    
    """
            --------------
    """
    st.session_state
    if "cookies" in st.session_state:
        if  cookies in st.session_state["cookies"] :
            if "UTM_Name" in st.session_state["cookies"][cookies]:
                if st.session_state["cookies"][cookies]["UTM_Name"] in st.session_state["Data"] :
                    UTM_Name_ = st.session_state["cookies"][cookies]["UTM_Name"]
                    poly_data = st.session_state["Data"][UTM_Name_]["poly_data"]
                    point_data = st.session_state["Data"][UTM_Name_]["point_data"]
                    data_point = st.session_state["Data"][UTM_Name_]["data_point"]
                    
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
                    
                    fig, ax = plt.subplots(figsize=(10, 10))
                    
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
                        offset_dist = sc*2  # ระยะ offset ออกนอก
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
                    
                    ax.set_title('\n' + UTM_Name_ + " " + poly_data['features'][0]['properties']['SURVEY_UNITNAME'] + '\n')
                    ax.axis("equal")
                    st.pyplot(fig)
                    
                    """
                        --------------
                    """
                    
                    h = len(data_point)
                    st.dataframe(data=data_point[['PCM_BNDNAME' , 'PCM_NORTH' , 'PCM_EAST']],width="stretch",height=35*(h+1))
                    """
                        --------------
                    """
                    c01, c02, c03 = st.columns([0.35,0.35,0.3])
                    Name_list = data_point["PCM_BNDNAME"].to_list()
                    point1 = c01.selectbox("หมุดหลักเขต 1",Name_list)
                    point2 = c02.selectbox("หมุดหลักเขต 2",Name_list)
                    if point1 == point2:
                        length = 0
                    else:
                        point1_ = data_point.loc[data_point['PCM_BNDNAME']==point1,'geometry'].iloc[0]
                        point2_ = data_point.loc[data_point['PCM_BNDNAME']==point2,'geometry'].iloc[0]
                        length = round(point1_.distance(point2_),3)
                    length_ = c03.selectbox("ระยะ",str(length))
                    
                    if length > 0 :
                        c1, c2 = st.columns([0.50,0.50])
                        number = c1.number_input("ระยะที่วัดได้",value=float(),step=0.001,format="%0.3f" )
                        if number != 0:
                            Diff = c2.text_input("ค่าต่าง",abs(round(length-float(number),3)))
        
