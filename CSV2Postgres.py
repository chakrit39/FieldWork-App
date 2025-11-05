import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from sqlalchemy import create_engine
st.set_page_config(page_title="Upload CSV to Postgis")

st.sidebar.header("Upload CSV to Postgis")
st.sidebar.markdown("แอปพลิเคชันนำเข้าข้อมูลภาคสนามเพื่อนำไปแก้ไขใน QGIS")
@st.cache_resource 
def get_postgis():
    HOSTNAME = st.secrets["HOSTNAME"]
    USER = st.secrets["USER"]
    PASSWD = st.secrets["PASSWD"]
    engine = create_engine( f"postgresql://{USER}:{PASSWD}@{HOSTNAME}:5432/Data1")
    return engine
            
@st.cache_data
def get_data():
    df_name = pd.read_csv("https://docs.google.com/spreadsheets/d/1taPadBX5zIlk80ZXc7Mn9fW-kK0VT-dgNfCcjRUskgQ/export?gid=0&format=csv",header=0)
    return df_name
    
engine = get_postgis()
df_name = get_data()
df_name_ = df_name[df_name[round_]==True]

if "Login" not in st.session_state:
    st.session_state["Login"] = False
else:
    st.session_state["Login"] = False
if "Submit" not in st.session_state:
    st.session_state["Submit"] = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "Refresh" not in st.session_state:
    st.session_state["Refresh"] = False

    
@st.dialog("สำเร็จ !!", width="small")
def pop_up():
    #st.write(f"Why is {item} your favorite?")
    #reason = st.text_input("Because...")
    if st.button("ตกลง"):
        #st.session_state.vote = {"item": item, "reason": reason}
        st.rerun()    
#[["องครักษ์","ONGKHARAK"],["ลำลูกกา","LUMLUKKA"],["ธัญบุรี","THANYABURI"],["คลองหลวง","KHLONGLUANG"],["ปทุมธานี","PATHUMTHANI"]]
#["องครักษ์", "ลำลูกกา", "ธัญบุรี", "คลองหลวง", "ปทุมธานี"]
st.title("Upload CSV file to PostGIS")
office = pd.DataFrame([["นครนายก","NAKHONNAYOK"]],columns=["th","eng"])
office_choice = st.selectbox("เลือกสำนักงานที่ดิน",["นครนายก"],)
office_select = office['eng'][office['th']==office_choice].iloc[0]
Noneheader = st.checkbox("None header")
Point = st.file_uploader("Upload a CSV file (Name,Code,N,E,h)", accept_multiple_files=False, type=['csv'],key=f"upload_{st.session_state.uploader_key}")
if Point is not None:
    if Noneheader == True:
        data = pd.read_csv(Point,header=None)
        data = data.rename(columns={0: "Name", 1: "Code", 2: "N", 3: "E", 4: "h"})
        st.dataframe(data,use_container_width=True)
    else:
        data = pd.read_csv(Point)
        st.dataframe(data,use_container_width=True)
        
#sql = f'SELECT * FROM "public"."BND_Points"'        
#gdf_postgis = gpd.GeoDataFrame.from_postgis(sql, engine, geom_col='geometry')
#gdf_postgis = gdf_postgis.sort_values(by=['Index'])
#gdf_postgis = gdf_postgis.reset_index(drop=True)
#df = data
#gdf = gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df['E'],df['N']) , crs="EPSG:24047")
#gdf = gdf.set_index(gdf.index + (gdf_postgis.tail(1)['Index'].iloc[0] + 1))
#st.dataframe(gdf_postgis.tail(1),use_container_width=True)
#st.dataframe(gdf,use_container_width=True)

"""
-----------------
"""
Name_list = df_name_["Name"].to_list()
Name = st.selectbox("ผู้รังวัด",Name_list,)
date = st.date_input("วันที่ทำการรังวัด",format="DD/MM/YYYY")
date_2 = str(date).split("-")
date_2 = int(str(int(date_2[0])+543)[-2:] + date_2[1] + date_2[2])
"""
-----------------
"""
c001, c002 = st.columns([0.12,0.88])
if c002.button("Refresh", type="primary"):
    st.session_state["Refresh"] = True
    get_postgis.clear()
    engine = get_postgis()
else:
    st.session_state["Refresh"] = False   
    
if c001.button("Submit"):
    st.session_state["Submit"] = True
    if Point is not None :
        if len(data) > 0:
            sql = f'SELECT * FROM "public"."BND_' + office_select + '"'
            gdf_postgis = gpd.GeoDataFrame.from_postgis(sql, engine, geom_col='geometry')
            if len(gdf_postgis) > 0:
                gdf_postgis = gdf_postgis.sort_values(by=['Index'])
                gdf_postgis = gdf_postgis.reset_index(drop=True)
            df = data
            df['Remark'] = df['Code']
            df['Surveyer'] = Name
            df['Date'] = date_2
            gdf = gpd.GeoDataFrame(df,geometry=gpd.points_from_xy(df['E'],df['N']) , crs="EPSG:24047")
            if len(gdf_postgis) > 0:
                gdf = gdf.set_index(gdf.index + (gdf_postgis.tail(1)['Index'].iloc[0] + 1))
            gdf.to_postgis("BND_"+office_select, engine, if_exists='append', index=True, index_label='Index')
            del st.session_state[f"upload_{st.session_state.uploader_key}"]
            st.session_state.uploader_key += 1
            pop_up()
        else:
            st.warning("ไม่มีข้อมูลในไฟล์ที่เลือก")
    else:
        st.warning("โปรดเลือกไฟล์")
else:
    st.session_state["Submit"] = False

#st.session_state  
  
