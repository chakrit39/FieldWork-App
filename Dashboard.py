import streamlit as st
import pandas as pd
import numpy as np
#from streamlit_folium import folium_static
##import folium as fo
import geopandas as gpd
#from requests.auth import HTTPBasicAuth
#import time
#import datetime
#import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
#from tempfile import NamedTemporaryFile
#from googleapiclient.discovery import build
#from googleapiclient.errors import HttpError
#from googleapiclient.http import MediaFileUpload
from sqlalchemy import create_engine

st.set_page_config(page_title="Dashboard")

#st.markdown("# Dashboard")
#st.sidebar.header("Dashboard")
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
@st.cache_data
def get_names_list(url):
    return pd.read_csv(url)
    
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
    
@st.cache_resource(ttl=21600)      
def get_postgis():
    HOSTNAME = st.secrets["HOSTNAME"]
    USER = st.secrets["USER"]
    PASSWD = st.secrets["PASSWD"]
    engine = create_engine( f"postgresql://{USER}:{PASSWD}@{HOSTNAME}:5432/Data1")
    return engine
    
tab1, tab2 = st.tabs(["Report Dashboard", "QField Dashboard"])


with tab1:
    st.header("Report Dashboard")
    
    # ดึง Service (ใช้ Resource Cache)
    creds, gc, sh, wks, wks_result = get_service()

    # 1. ปรับการเลือก รอบ (ใช้ index เพื่อจำค่าเดิมได้ดีขึ้น)
    round_options = ["รอบที่ 1", "รอบที่ 2", "รอบที่ 3", "รอบที่ 4", "ทั้งหมด"]
    selected_round = st.selectbox("เลือกรอบ", round_options)
    
    suffix = "" if selected_round == "ทั้งหมด" else selected_round

    # 2. ใช้ Cache ในการดึงข้อมูลจาก Worksheet (เพื่อความรวดเร็ว)
    @st.cache_data(ttl=600) # เก็บ Cache ไว้ 10 นาที
    def fetch_gsheet_data(_wks_result):
        return pd.DataFrame(_wks_result.get_all_records())

    df_raw = fetch_gsheet_data(wks_result)

    # 3. กรอง Column ตามรอบที่เลือก
    col_marker_cnt = 'จำนวนหมุดหลักเขต ' + suffix
    col_parcel_cnt = 'จำนวนแปลง ' + suffix
    col_marker_tgt = 'หมุดเป้าหมาย ' + suffix
    col_parcel_tgt = 'แปลงเป้าหมาย ' + suffix

    # เลือกเฉพาะคอลัมน์ที่ใช้งาน
    df = df_raw[['Name', col_marker_cnt, col_parcel_cnt, col_marker_tgt, col_parcel_tgt]].copy()
    
    # กรองเฉพาะแถวที่มีเป้าหมาย > 0 เพื่อไม่ให้กราฟ/ตารางรก
    df = df[df[col_parcel_tgt] != 0].reset_index(drop=True)

    # 4. คำนวณ Progress แบบปลอดภัย (Handling Division by Zero)
    def calc_progress(row):
        # กันเหนียวถ้าเป้าหมายเป็น 0 ให้ progress เป็น 0
        p_parcel = (row[col_parcel_cnt] / row[col_parcel_tgt] * 100) if row[col_parcel_tgt] > 0 else 0
        p_marker = (row[col_marker_cnt] / row[col_marker_tgt] * 100) if row[col_marker_tgt] > 0 else 0
        return round(min(p_parcel, p_marker), 2)

    df['Progress'] = df.apply(calc_progress, axis=1)

    # เปลี่ยนชื่อ Column ให้ดูง่ายในตาราง
    df_display = df.rename(columns={
        col_parcel_tgt: 'แปลงเป้าหมาย',
        col_parcel_cnt: 'จำนวนแปลง',
        col_marker_tgt: 'หมุดเป้าหมาย',
        col_marker_cnt: 'จำนวนหมุดหลักเขต'
    })

    # 5. แสดงตาราง
    st.dataframe(
        df_display,
        column_config={
            "Progress": st.column_config.ProgressColumn(
                "ความคืบหน้า (%)",
                format="%.2f%%",
                min_value=0,
                max_value=100,
            ),
        },
        use_container_width=True,
        height=35 * (len(df_display) + 1)
    )

    # 6. ปุ่ม Refresh (ล้าง Cache เฉพาะจุด)
    if st.button("Refresh Report Data",type="primary"):
        fetch_gsheet_data.clear()
        st.rerun()
        
with tab2:
    st.header("QField Dashboard")
    
    # 1. เลือกสำนักงาน
    office_list = ['ศรีราชา','บางละมุง','สัตหีบ'] 
    office_select = st.selectbox("สำนักงานที่ดิน", office_list)
    
    office_mapping = pd.DataFrame([
        ["องครักษ์","ONGKHARAK"],["ลำลูกกา","LUMLUKKA"],["ธัญบุรี","THANYABURI"],
        ["คลองหลวง","KHLONGLUANG"],["ปทุมธานี","PATHUMTHANI"],["นครนายก","NAKHONNAYOK"],
        ["ศรีราชา","SRIRACHA"],["บางละมุง","BANGLAMUNG"],["สัตหีบ","SATTAHIP"]
    ], columns=["th","eng"])
    
    office_choice = office_mapping['eng'][office_mapping['th'] == office_select].iloc[0]

    # 2. เชื่อมต่อ Database และดึงเฉพาะผลสรุป (Aggregation)
    # วิธีนี้จะดึงแค่ตารางเล็กๆ ที่มีผลรวมมา ไม่ดึงพิกัดแผนที่มาให้หนัก RAM
    engine = get_postgis()
    
    # SQL นับจำนวนแปลงที่ FINISH = 1 แยกตามรายชื่อ (CODE_N)
    sql_parcel = f"""
        SELECT "CODE_N", COUNT(*) as count 
        FROM "public"."L2_{office_choice}" 
        WHERE "FINISH" = 1 
        GROUP BY "CODE_N"
    """
    
    # SQL นับจำนวนหมุด แยกตาม Surveyer
    sql_marker = f"""
        SELECT "Surveyer", COUNT(*) as count 
        FROM "public"."BND_{office_choice}" 
        GROUP BY "Surveyer"
    """

    try:
        with st.spinner('กำลังประมวลผลข้อมูลจากฐานข้อมูล...'):
            df_parcel_counts = pd.read_sql(sql_parcel, engine)
            df_marker_counts = pd.read_sql(sql_marker, engine)

        # 3. โหลดรายชื่อผู้รังวัด (ใช้ Cache)
        names_url = "https://docs.google.com/spreadsheets/d/1taPadBX5zIlk80ZXc7Mn9fW-kK0VT-dgNfCcjRUskgQ/export?gid=0&format=csv"
        df_name = get_names_list(names_url)
        df_active = df_name[["ลำดับ", "Name"]].copy()

        # 4. Matching ข้อมูล
        # แปลงผลลัพธ์จาก SQL เป็น Dictionary เพื่อ Mapping
        parcel_dict = dict(zip(df_parcel_counts['CODE_N'].astype(str), df_parcel_counts['count']))
        marker_dict = dict(zip(df_marker_counts['Surveyer'].astype(str), df_marker_counts['count']))

        df_active['จำนวนแปลง'] = df_active['ลำดับ'].astype(str).map(parcel_dict).fillna(0)
        
        # คำนวณจำนวนหมุดตามสูตรเดิมของคุณ
        df_active['จำนวนหมุด'] = df_active['Name'].map(marker_dict).apply(
            lambda x: round((x/3)-0.5, 0) if pd.notnull(x) and x > 0 else 0
        )

        # 5. แสดงผล
        df_display = df_active[df_active['จำนวนแปลง'] > 0].copy()
        df_display = df_display[["Name", "จำนวนแปลง", "จำนวนหมุด"]]
        
        h_display = len(df_display)
        st.dataframe(
            df_display,
            use_container_width=True,
            height=35 * (h_display + 1)
        )

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        
    # 6. ปุ่ม Refresh
    if st.button("Refresh Data", type="primary", key="qfield_refresh"):
        get_postgis.clear()
        get_names_list.clear()
        st.rerun()
