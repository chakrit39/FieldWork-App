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
    wks_result = sh.worksheet('Result')
    return creds,gc,sh,wks,wks_result
#icon_image = url("leaf-red.png")
#icon = folium.CustomIcon(icon_image,icon_size=(38, 95),icon_anchor=(22, 94))
@st.cache_resource 
def get_map():    
    gdf_t = gpd.read_file('/vsicurl/https://github.com/chakrit39/FieldWork-App/raw/refs/heads/main/Tambon/องครักษ์.shp')
    gdf_t = gdf_t.to_crs('EPSG:4326')
    map = fo.Map(location=[14.078746259525621, 101.02592277876519], zoom_start=11)
    round1 = ["บึงศาล","บางสมบูรณ์","ชุมพล","พระอาจารย์","บางลูกเสือ","ศีรษะกระบือ"]
    for _, t in gdf_t.iterrows():
        # Without simplifying the representation of each borough,
        # the map might not be displayed
        sim_geo = gpd.GeoSeries(t["geometry"]).simplify(tolerance=0.001)
        geo_j = sim_geo.to_json()
        if round1.count(t["T_NAME_T"])==1:
            geo_j = fo.GeoJson(data=geo_j)
        else:
            geo_j = fo.GeoJson(data=geo_j,style_function=lambda x: {"fillOpacity": 0})
        fo.Popup(t["T_NAME_T"]).add_to(geo_j)
        geo_j.add_to(map)
        #tile = fo.TileLayer(tiles = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',attr = 'Esri',name = 'Esri Satellite',overlay = False,control = True).add_to(map)
    return map
def get_Refresh():    
    get_map.clear()
    map = get_map()
    
st.title("Dashboard")
creds,gc,sh,wks,wks_result = get_service()

df =  pd.DataFrame(wks_result.get_all_records())  
df['Progress'] = round(100/ df['เป้าหมาย'] * df['จำนวนแปลง'],2)
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
    use_container_width=True
)


st.header('Map')
map = get_map()

gdf = gpd.GeoDataFrame(wks.get_all_records())
Name = st.selectbox("ผู้รังวัด",["ทั้งหมด","ชาคฤตย์", "กิตติพันธุ์", "สุริยา", "ณัฐพร", "ศรัณย์", "ฐณิตา", "ปณิดา", "ปฐพี"],on_change=get_Refresh())
if st.button("Refresh"):
    st.session_state["Refresh"] = True
    get_map.clear()
    get_service.clear()
    map = get_map()
    creds,gc,sh,wks,wks_result = get_service()
else:
    st.session_state["Refresh"] = False
    
if len(gdf)!=0:  
    if Name != "ทั้งหมด":
        gdf = gdf[gdf['ผู้รังวัด']==Name]
    gdf = gdf.set_geometry(gpd.points_from_xy(gdf.E,gdf.N),crs='EPSG:24047')
    st.dataframe(data=gdf)
    gdf = gdf.to_crs(4326)
    st.dataframe(data=gdf)
    gdf.crs
    #lat = gdf.geometry.y
    #lon = gdf.geometry.x
    #fo.CircleMarker([lat,lon],radius = 3,color='#f56042',fill=True,fill_opacity=1).add_to(map)
    for lat,lon in zip(gdf.geometry.y,gdf.geometry.x):
        fo.CircleMarker([lat,lon],radius=3,color='#f56042',fill=True,fill_opacity=1).add_to(map)
folium_static(map)
