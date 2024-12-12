import streamlit as st
import pandas as pd
import numpy as np
import geopandas as gpd
from sqlalchemy import create_engine

HOSTNAME = '122.155.131.34'
USER = "postgres"
PASSWD = "KTP5Admin"
engine = create_engine( f"postgresql://{USER}:{PASSWD}@{HOSTNAME}:7001/Data1")

st.set_page_config(page_title="Upload CSV to Postgis")

st.sidebar.header("Upload CSV to Postgis")

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

st.title("Upload CSV file to PostGIS")

Noneheader = st.checkbox("None header")
Point = st.file_uploader("Upload a CSV file (Name,Code,N,E,h)", accept_multiple_files=False, type=['csv'])
if Point is not None:
    if Noneheader == True:
        data = pd.read_csv(Point,header=None)
        data = data.rename(columns={0: "Name", 1: "Code", 2: "N", 3: "E", 4: "h"})
    else:
        data = pd.read_csv(Point)


"""
-----------------
"""
Name = st.selectbox("ผู้รังวัด",["ชาคฤตย์", "กิตติพันธุ์", "สุริยา", "ณัฐพร", "ศรัณย์", "ฐณิตา", "ปณิดา", "ปฐพี"],)
date = st.date_input("วันที่ทำการรังวัด",format="DD/MM/YYYY")
"""
-----------------
"""
c001, c002 = st.columns([0.12,0.88])
if c001.button("Submit"):
    st.session_state["Submit"] = True
    if Point is not None :
        if len(data) > 0:
            sql = f"SELECT * FROM Points ;"
            gdf_postgis = gpd.GeoDataFrame.from_postgis(sql, engine, geom_col='geometry')
            df = data
            df['Remark'] = df['Code']
            df['ผู้รังวัด'] = Name
            df['Date'] = '671212'
        else:
            st.warning("ไม่มีข้อมูลในไฟล์ที่เลือก")
    else:
        st.warning("โปรดเลือกไฟล์")
else:
    st.session_state["Submit"] = False

if c002.button("Refresh", type="primary"):
    st.session_state["Refresh"] = True
else:
    st.session_state["Refresh"] = False   
#st.session_state  
  