import streamlit as st
import pandas as pd
import numpy as np
from streamlit_folium import folium_static
import folium as fo
import geopandas as gpd
from requests.auth import HTTPBasicAuth
import time
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from tempfile import NamedTemporaryFile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

st.set_page_config(page_title="Dashboard")

#st.markdown("# Dashboard")
st.sidebar.header("Dashboard")
if "Login" not in st.session_state:
    st.session_state["Login"] = False
else:
    st.session_state["Login"] = False
if "Refresh" not in st.session_state:
    st.session_state["Refresh"] = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
scope = ['https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/spreadsheets',
        ]

@st.cache_resource 
def get_service():
    #if "creds" not in globals() :
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["dol-mtd5-fieldwork"], scope)
    gc = gspread.authorize(creds)
    sh = gc.open('องครักษ์')
    wks = sh.worksheet('Raw')
    wks_result = gc.open('Total_Result').worksheet('Result')
    return creds,gc,sh,wks,wks_result
#icon_image = url("leaf-red.png")
#icon = folium.CustomIcon(icon_image,icon_size=(38, 95),icon_anchor=(22, 94))
@st.cache_resource 
def get_map():
    df_field = pd.read_csv("https://docs.google.com/spreadsheets/d/1df9H6WDQX9KXAEIOkNF298jE-UU63wEl0FSB4OdH8k8/export?gid=0&format=csv",header=0)
    gdf_t = gpd.read_file('/vsicurl/https://github.com/chakrit39/FieldWork-App/raw/refs/heads/main/Tambon/ตำบล.shp')
    gdf_t = gdf_t.to_crs('EPSG:4326')
    map = fo.Map(location=[14.078746259525621, 101.02592277876519], zoom_start=11)
    round_ = {"รอบที่ 1" : df_field["พื้นที่"][df_field["รอบ"]=="รอบที่ 1"].iloc[0].split(","),
              #"รอบที่ 2" : df_field["พื้นที่"][df_field["รอบ"]=="รอบที่ 2"].iloc[0].split(","),
              #"รอบที่ 3" : df_field["พื้นที่"][df_field["รอบ"]=="รอบที่ 3"].iloc[0].split(","),
              #"รอบที่ 4" : df_field["พื้นที่"][df_field["รอบ"]=="รอบที่ 4"].iloc[0].split(",")
             }
    if Round == "":
        round_field = round_["รอบที่ 1"]
        round_field.extend(round_["รอบที่ 2"])
        round_field.extend(round_["รอบที่ 3"])
        round_field.extend(round_["รอบที่ 4"])
        round_field = list(set(round_field))
    else:
        round_field = round_[Round]
    for _, t in gdf_t.iterrows():
        # Without simplifying the representation of each borough,
        # the map might not be displayed
        sim_geo = gpd.GeoSeries(t["geometry"]).simplify(tolerance=0.001)
        geo_j = sim_geo.to_json()
        if round_field.count(t["T_NAME_T"])==1:
            geo_j = fo.GeoJson(data=geo_j)
        else:
            geo_j = fo.GeoJson(data=geo_j,style_function=lambda x: {"fillOpacity": 0})
        fo.Popup(t["T_NAME_T"]).add_to(geo_j)
        geo_j.add_to(map)
        #tile = fo.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google Satellite',name='Google Satellite', overlay=True).add_to(map)
        #tile = fo.TileLayer(tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',attr = 'Esri',name = 'Esri Satellite',overlay = False,control = True).add_to(map)
    return map
def get_Refresh():    
    get_map.clear()
    map = get_map()
def get_Refresh2():    
    get_map.clear()

st.title("Dashboard")
creds,gc,sh,wks,wks_result = get_service()

Round_ = st.selectbox("เลือกรอบ ",["รอบที่ 1","รอบที่ 2","รอบที่ 3","รอบที่ 4", "ทั้งหมด"],on_change=get_Refresh2())
if Round_ == "ทั้งหมด":
    Round = ""
else:
    Round = Round_
df_ =  pd.DataFrame(wks_result.get_all_records())  
df = df_[['Name','จำนวนหมุดหลักเขต ' + Round, 'จำนวนแปลง ' + Round, 'หมุดเป้าหมาย ' + Round, 'แปลงเป้าหมาย ' + Round]]
df = df[df['แปลงเป้าหมาย ' + Round]!=0]
df = df.reset_index(drop=True)
df['Progress'] = 0
h = len(df)
for i in range(h):
    if round(100/ df['แปลงเป้าหมาย ' + Round][i] * df['จำนวนแปลง ' + Round][i],2) < round(100/ df['หมุดเป้าหมาย ' + Round][i] * df['จำนวนหมุดหลักเขต ' + Round][i],2):
        df['Progress'][i] = round(100/ df['แปลงเป้าหมาย ' + Round][i] * df['จำนวนแปลง ' + Round][i],2)
    else:
        df['Progress'][i] = round(100/ df['หมุดเป้าหมาย ' + Round][i] * df['จำนวนหมุดหลักเขต ' + Round][i],2)
df = df.rename(columns={'แปลงเป้าหมาย ' + Round : 'แปลงเป้าหมาย', 'จำนวนแปลง ' + Round : 'จำนวนแปลง' , 'หมุดเป้าหมาย ' + Round : 'หมุดเป้าหมาย' , 'จำนวนหมุดหลักเขต ' + Round : 'จำนวนหมุดหลักเขต'}, errors="raise")
#df_ = df.tail(1).copy()
#df = df.drop([df_.index[0]])
st.dataframe(
    df,
    column_config={
        "Progress": st.column_config.ProgressColumn(
            "Progress",
            help="The sales volume in USD",
            format="%f %%",
            min_value=0,
            max_value=100,
        ),
    },
    #hide_index=True,
    width="stretch",
    height=None
)

st.write(df.to_html(), unsafe_allow_html=True)
#st.header('Map')
#map = get_map()

#Name_list_ = df["Name"].to_list()
#Name_list_ = Name_list_[0:len(Name_list_)-1]
#Name_list = ["ทั้งหมด"]
#Name_list.extend(Name_list_)
#Name = st.selectbox("ผู้รังวัด",Name_list,on_change=get_Refresh())
if st.button("Refresh"):
    st.session_state["Refresh"] = True
    #get_map.clear()
    get_service.clear()
    #map = get_map()
    #creds,gc,sh,wks,wks_result = get_service()
else:
    st.session_state["Refresh"] = False
#gdf_ong = pd.DataFrame(gc.open('องครักษ์').worksheet('Raw').get_all_records())   
#gdf_lum = pd.DataFrame(gc.open('ลำลูกกา').worksheet('Raw').get_all_records())  
#gdf_thun = pd.DataFrame(gc.open('ธัญบุรี').worksheet('Raw').get_all_records())  
#gdf_khlong = pd.DataFrame(gc.open('คลองหลวง').worksheet('Raw').get_all_records())  
#gdf_pathum = pd.DataFrame(gc.open('ปทุมธานี').worksheet('Raw').get_all_records())  
#gdf_ = gpd.GeoDataFrame(pd.concat([gdf_ong,gdf_lum,gdf_thun,gdf_khlong,gdf_pathum]))
#if Round_ != "ทั้งหมด":
#    gdf = gdf_[gdf_["รอบ"]==Round]
#    gdf = gdf.reset_index(drop=True)
#else:
#    gdf = gdf_
#if len(gdf)!=0:  
#    if Name != "ทั้งหมด":
#        gdf = gdf[gdf['ผู้รังวัด']==Name]
#    gdf = gdf.set_geometry(gpd.points_from_xy(gdf.E,gdf.N),crs='EPSG:24047')
    #st.dataframe(data=gdf)
#    gdf = gdf.to_crs(epsg=4326)
    #st.dataframe(data=gdf)
    #gdf.crs
    #lat = gdf.geometry.y
    #lon = gdf.geometry.x
    #fo.CircleMarker([lat,lon],radius = 3,color='#f56042',fill=True,fill_opacity=1).add_to(map)
#    for lat,lon in zip(gdf.geometry.y,gdf.geometry.x):
#        fo.CircleMarker([lat,lon],radius=3,color='#f56042',fill=True,fill_opacity=1).add_to(map)
#folium_static(map)
