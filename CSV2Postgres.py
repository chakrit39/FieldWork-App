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
Point = st.file_uploader("Upload a CSV file (Name,Code,N,E,H)", accept_multiple_files=False, type=['csv'])
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

c001, c002 = st.columns([0.12,0.88])
if c001.button("Submit"):
    #import time 
    #start = time.time()
    st.session_state["Submit"] = True
    if N1!="" and N2!="" and N3!="" and E1!="" and E2!="" and E3!="" and N3!="" and E1!="" and E2!="" and E3!="" and H1!="" and H2!=""and H3!="" and parcel_no!="" and survey_no!="" and land_no!="" and UTMMAP1!="" and UTMMAP3!="" and BND_NAME!="" :
        if sh_report.title != Name+'-Report':
            sh_report = gc.open(Name+'-Report')
        N = round((float(N1)+float(N2)+float(N3))/3,3)
        E = round((float(E1)+float(E2)+float(E3))/3,3)
        H = round((float(H1)+float(H2)+float(H3))/3,3)
        if image_1 and image_2 and image_3:
            image_id = []
            image = [image_1,image_2,image_3]
            folder_id = ["1HTrQBM08XN_q8DpGma72eeLhI8rJYbl9", "1MYq0n532WluOCcju_aMFlJWPPswA5IBU","1w2M2CNUNeAm4uIXb3BV6mA1wdPC72rE3"]
            for i in range(3):
                image_id.append(upload_image(service,folder_id[i],image[i]))
            row = [parcel_no, survey_no, province, amphoe, tambon, UTMMAP1, UTMMAP2, UTMMAP3, UTMMAP4, Scale, land_no, Name, BND_NAME, N, E, H, Method, date.strftime('%d/%m/%Y'), remark, N1, E1, H1, N2, E2, H2, N3, E3, H3,image_id[0],image_id[1],image_id[2]]
            row_update = wks.append_row(values=row,value_input_option="USER_ENTERED")
            DATE_temp = wks.acell('R'+row_update['updates']['updatedRange'][5:]).value.replace('\xa0',' ').split()
            DATE = DATE_temp[0] + " " + DATE_temp[1] + " " + str(int(DATE_temp[2])+543)
            create_report()
            del st.session_state[f"image_1-{st.session_state.uploader_key}"]
            del st.session_state[f"image_2-{st.session_state.uploader_key}"]
            del st.session_state[f"image_3-{st.session_state.uploader_key}"]
            st.session_state.uploader_key += 1
            #st.rerun()
            #st.success('สำเร็จ!', icon="✅")
            #end = time.time()
            #end - start
            pop_up()
        else:
            st.warning("โปรดเลือกรูปภาพให้ครบ")
    else:
        st.warning("โปรดกรอกข้อมูลให้ครบถ้วน")
else:
    st.session_state["Submit"] = False

if c002.button("Refresh", type="primary"):
    st.session_state["Refresh"] = True
    creds,gc,service,sh,wks,sh_ref,wks_ref,sh_report = get_service()
else:
    st.session_state["Refresh"] = False   
#st.session_state  
  
