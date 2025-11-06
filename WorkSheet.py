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
register_heif_opener()
st.set_page_config(page_title="WorkSheet")

st.sidebar.header("Work Sheets")
st.sidebar.markdown("แอปพลิเคชันสร้างรายงานจากข้อมูลภาคสนาม")

if "Submit" not in st.session_state:
    st.session_state["Submit"] = False
if "Search" not in st.session_state:
    st.session_state["Search"] = False
if "Login" not in st.session_state:
    st.session_state["Login"] = False
if "Login_alert" not in st.session_state:
    st.session_state["Login_alert"] = False
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
if "Refresh" not in st.session_state:
    st.session_state["Refresh"] = False
scope = ['https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/drive.file',
         'https://www.googleapis.com/auth/spreadsheets',
        ]
def upload_image(service,parents,image_i):
    file_name = str(UTMMAP1) + str(UTMMAP2) + str(UTMMAP3) + "-" + str(UTMMAP4) + "-" + str(Scale) + "-" + str(land_no) + "_" + BND_NAME + ".jpeg"
    path = "./Temp/" +  file_name
    
    img = Image.open(image_i)
    size = img._size
    if size[0] > size[1]:
        chk_sc = size[0]
    else:
        chk_sc = size[1]
    if chk_sc > 2000:
        sc = chk_sc/2000
        new_img = img.resize( ( int(round(size[0]/sc,0)) , int(round(size[1]/sc,0)) ) )
    else:
        new_img = img
    if new_img.mode != "RGB":
        new_img = new_img.convert('RGB')
    new_img.save(path)
    #temp_file = open(path, 'wb')
    #temp_file.write(new_img.getvalue())
    #temp_file.close()
    file_metadata = {"name": file_name,"parents": [parents]}
    media = MediaFileUpload(path, mimetype="image/jpeg")
    file = (service.files().create(body=file_metadata, media_body=media, fields="id").execute() )
    file_id = file['id']
    del media
    del file
    del file_metadata
    os.remove(path)
    return file_id
    
@st.cache_resource 
def get_service():
    #if "creds" not in globals() :
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["dol-mtd5-fieldwork"], scope)
    gc = gspread.authorize(creds)
    service = build("drive", "v3", credentials=creds)
    sh = gc.open(office_select)
    wks = sh.worksheet('Raw')
    wks_reg = sh.worksheet('REG')
    
    #sh_report = gc.open(Name+'-Report_'+office_select)
    return creds,gc,service,sh,wks,wks_reg#,sh_report
    
@st.cache_data
def get_reg():
    df_reg = pd.DataFrame(wks.get_all_records(numericise_ignore=['all']))
    return df_reg
    
@st.cache_resource 
def get_postgis():
    HOSTNAME = st.secrets["HOSTNAME"]
    USER = st.secrets["USER"]
    PASSWD = st.secrets["PASSWD"]
    engine = create_engine( f"postgresql://{USER}:{PASSWD}@{HOSTNAME}:5432/Data1")
    return engine
    
@st.cache_data
def get_data():
    df = pd.read_csv('./P_A_T.csv',header=0)
    sc = pd.read_csv('./UTMMAP4.csv',header=0,dtype={'UTMMAP4': str})
    df_name = pd.read_csv("https://docs.google.com/spreadsheets/d/1taPadBX5zIlk80ZXc7Mn9fW-kK0VT-dgNfCcjRUskgQ/export?gid=0&format=csv",header=0)
    df_fol = pd.read_csv("https://docs.google.com/spreadsheets/d/1j0m_zhMDIXrqjsqyRMCczHjm6quwVS4Km0M7WqZ_s2M/export?gid=0&format=csv",header=0)
    return df,sc,df_name,df_fol
    
@st.dialog("สำเร็จ !!", width="small")
def pop_up():
    #st.write(f"Why is {item} your favorite?")
    #reason = st.text_input("Because...")
    if st.button("ตกลง"):
        #st.session_state.vote = {"item": item, "reason": reason}
        st.rerun()    
        
Office = ['นครนายก']        
placeholder = st.empty()
with placeholder.form("login"):
    st.markdown("#### โปรดเลือก")
    office_select = st.selectbox("สำนักงานที่ดิน",Office)
    round_ = st.selectbox("รอบที่",["1"])
    Login = st.form_submit_button("Login")
    if Login:
        st.session_state["Login"] = True
        st.session_state["Login_alert"] = True
        
if st.session_state["Login"]:
    office_select = office_select
    round_ = "รอบที่ " + round_
    placeholder.empty()
    if st.session_state["Login_alert"] == True:
        st.success("Login successful")
    
 
    df,sc,df_name,df_fol = get_data()
    engine = get_postgis()
    df_name_ = df_name[df_name[round_]==True]
    df_fol_ = df_fol[df_fol.Name==office_select]
    df_fol_ = df_fol_.reset_index(drop=True)
    folder_id = [df_fol_.iloc[0,1], df_fol_.iloc[0,2],df_fol_.iloc[0,3]]
    df_P_A_T = df[df['OFFICE']==office_select]
    df_P_A_T = df_P_A_T.reset_index(drop=True)

    creds,gc,service,sh,wks,wks_reg = get_service()
    df_reg = get_reg()
    
    st.title("แบบกรอกข้อมูลงานภาคสนาม")
    st.title("สาขา"+office_select)  
    col_1, col_2, col_3, col_4, col_5 , col_6 = st.columns([0.18,0.13,0.18,0.18,0.13,0.15])
    UTMMAP1 = col_1.text_input("UTMMAP1","")
    UTMMAP2 = col_2.selectbox("UTMMAP2",["I", "II", "III", "IV"],)
    UTMMAP3 = col_3.text_input("UTMMAP3","")
    Scale = col_4.selectbox("Scale",pd.unique(sc.SCALE),)
    UTMMAP4 = col_5.selectbox("UTMMAP4",pd.unique(sc.UTMMAP4[sc.SCALE==Scale]),)
    land_no = col_6.text_input("เลขที่ดิน","")
    df_reg
    if st.button("Search"):
        if UTMMAP1 != "" and UTMMAP2 != "" and UTMMAP3 != "" and UTMMAP4 != "" and Scale != "" and land_no != "" :
            UTM_Search = str(UTMMAP1) + str(UTMMAP2) + str(UTMMAP3) + str(UTMMAP4) + str(Scale) + str(land_no)
            df_reg_ = df_reg[df_reg['REG_JOIN']==UTM_Search]
            df_reg_ = df_reg_.reset_index(drop=True)
            if len(df_reg_) == 1:
                st.session_state["Search"] = True
            else:
                st.session_state["Search"] = False
                st.warning("ไม่พบข้อมูลในทะเบียน")
        else:
            st.session_state["Search"] = False
            st.warning("โปรดกรอกข้อมูลในครบถ้วน")
            
    if st.session_state["Search"] == True:
        c01, c02 = st.columns([0.50,0.50])
        parcel_no = c01.text_input("เลขที่โฉนด","")
        survey_no = c02.text_input("หน้าสำรวจ","")
    
        col1, col2, col3 = st.columns([0.35,0.35,0.3])
        province = col1.selectbox("จังหวัด",pd.unique(df_P_A_T.P_NAME_T))
        amphoe = col2.selectbox("อำเภอ",pd.unique(df_P_A_T.A_NAME_T[df_P_A_T.P_NAME_T==province]))
        tambon = col3.selectbox("ตำบล",pd.unique(df_P_A_T.T_NAME_T[df_P_A_T.A_NAME_T==amphoe]))

    #c01, c02 = st.columns([0.50,0.50])
    #parcel_no = c01.text_input("เลขที่โฉนด","")
    #survey_no = c02.text_input("หน้าสำรวจ","")

    #col1, col2, col3 = st.columns([0.35,0.35,0.3])
    #province = col1.selectbox("จังหวัด",pd.unique(df_P_A_T.P_NAME_T))
    #amphoe = col2.selectbox("อำเภอ",pd.unique(df_P_A_T.A_NAME_T[df_P_A_T.P_NAME_T==province]))
    #tambon = col3.selectbox("ตำบล",pd.unique(df_P_A_T.T_NAME_T[df_P_A_T.A_NAME_T==amphoe]))
    
    """
    --------------
    """
    cc1, cc2 = st.columns([0.5,0.5])
    BND_NAME = cc1.text_input("ชื่อหลักเขต","")
    Method = cc2.selectbox("เครื่องมือการรังวัด",["RTK GNSS","Total Station"])
    chk1, chk2 = st.columns([0.5,0.5])
    upload_method = chk1.selectbox("เลือกวิธีการนำเข้า",["ป้อนค่าพิกัด","Upload a CSV file (Name,Code,N,E,h)","Import from PostGIS"])
    Diff = chk2.text_input("ค่าต่างสูงสุด (m.)","")
    if upload_method == "ป้อนค่าพิกัด":
        c1, c2, c3 = st.columns([0.4,0.4,0.2])
        N1 = c1.text_input("N1","")
        N2 = c1.text_input("N2","")
        N3 = c1.text_input("N3","")
    
        E1 = c2.text_input("E1","")
        E2 = c2.text_input("E2","")
        E3 = c2.text_input("E3","")
    
        H1 = c3.text_input("H1","")
        H2 = c3.text_input("H2","")
        H3 = c3.text_input("H3","")    
    elif upload_method == "Upload a CSV file (Name,Code,N,E,h)":
        chk2.write("")
        chk2.write("")
        Noneheader = chk1.checkbox("None header")
        Point = st.file_uploader("เลือกไฟล์ CSV", accept_multiple_files=False, type=['csv'])
        if Point is not None:
            if Noneheader == True:
                data = pd.read_csv(Point,header=None)
                data = data.rename(columns={0: "Name", 1: "Code", 2: "N", 3: "E", 4: "h"})
            else:
                data = pd.read_csv(Point)
            #st.dataframe(data=data['Code'].unique(),use_container_width=False)
            if BND_NAME != "" :
                data_point = data[['Code','N','E','h']][data.Code==BND_NAME]
                data_point = data_point.reset_index(drop=True)
                if len(data_point)==3:
                    st.dataframe(data=data_point,use_container_width=True)
                    c1, c2, c3 = st.columns([0.4,0.4,0.2])
                    N1 = c1.text_input("N1",data_point.iloc[0,1])
                    N2 = c1.text_input("N2",data_point.iloc[1,1])
                    N3 = c1.text_input("N3",data_point.iloc[2,1])
    
                    E1 = c2.text_input("E1",data_point.iloc[0,2])
                    E2 = c2.text_input("E2",data_point.iloc[1,2])
                    E3 = c2.text_input("E3",data_point.iloc[2,2])
    
                    H1 = c3.text_input("H1",data_point.iloc[0,3])
                    H2 = c3.text_input("H2",data_point.iloc[1,3])
                    H3 = c3.text_input("H3",data_point.iloc[2,3])
                elif len(data_point)==0:
                    st.warning("ไม่พบชื่อหมุดหลักเขต")
                else:
                    st.dataframe(data=data_point,use_container_width=True)
                    st.warning("จำนวนค่าพิกัดหมุดหลักเขตไม่ครบหรือเกิน 3 ค่า")
            else:
                st.warning("โปรดใส่ชื่อหมุดหลักเขต")
    elif upload_method == "Upload a CSV file (PostGIS)":
        chk2.write("")
        chk2.write("")
        Noneheader = chk1.checkbox("None header")
        Point = st.file_uploader("เลือกไฟล์ CSV", accept_multiple_files=False, type=['csv'])
        if Point is not None:
            if Noneheader == True:
                data = pd.read_csv(Point,header=None)
                data = data.rename(columns={0: "Name", 1: "Code", 2: "N", 3: "E", 4: "h"})
            else:
                data = pd.read_csv(Point)
            #st.dataframe(data=data['Code'].unique(),use_container_width=False)
            if BND_NAME != "" :
                data_point = data[['NAME','CODE','N','E','H','REMARK','DATE']][data.CODE==BND_NAME]
                data_point = data_point.reset_index(drop=True)
                if len(data_point)==3:
                    st.dataframe(data=data_point,use_container_width=True)
                    c1, c2, c3 = st.columns([0.4,0.4,0.2])
                    N1 = c1.text_input("N1",data_point.iloc[0,2])
                    N2 = c1.text_input("N2",data_point.iloc[1,2])
                    N3 = c1.text_input("N3",data_point.iloc[2,2])
                    E1 = c2.text_input("E1",data_point.iloc[0,3])
                    E2 = c2.text_input("E2",data_point.iloc[1,3])
                    E3 = c2.text_input("E3",data_point.iloc[2,3])
                    H1 = c3.text_input("H1",data_point.iloc[0,4])
                    H2 = c3.text_input("H2",data_point.iloc[1,4])
                    H3 = c3.text_input("H3",data_point.iloc[2,4])
                elif len(data_point)==0:
                    st.warning("ไม่พบชื่อหมุดหลักเขต")
                else:
                    st.dataframe(data=data_point,use_container_width=True)
                    st.warning("จำนวนค่าพิกัดหมุดหลักเขตไม่ครบหรือเกิน 3 ค่า")
            else:
                st.warning("โปรดใส่ชื่อหมุดหลักเขต")
    elif upload_method == "Import from PostGIS":
        office_ = pd.DataFrame([["องครักษ์","ONGKHARAK"],["ลำลูกกา","LUMLUKKA"],["ธัญบุรี","THANYABURI"],["คลองหลวง","KHLONGLUANG"],["ปทุมธานี","PATHUMTHANI"]],columns=["th","eng"])
        office_choice = office_['eng'][office_['th']==office_select].iloc[0]
        sql = f'SELECT * FROM "public"."BND_' + office_choice + '"'
        gdf_postgis = gpd.GeoDataFrame.from_postgis(sql, engine, geom_col='geometry')
        gdf_postgis_new = gdf_postgis[['Name','Code','N','E','h','Remark','Date']] #[gdf_postgis['ผู้รังวัด']==Name]
        if BND_NAME != "" :
            data_point = gdf_postgis_new[['Name','Code','N','E','h','Remark','Date']][gdf_postgis_new.Code==BND_NAME]
            data_point = data_point.reset_index(drop=True)
            if len(data_point)==3:
                 st.dataframe(data=data_point,use_container_width=True)
                 c1, c2, c3 = st.columns([0.4,0.4,0.2])
                 N1 = c1.text_input("N1",data_point.iloc[0,2])
                 N2 = c1.text_input("N2",data_point.iloc[1,2])
                 N3 = c1.text_input("N3",data_point.iloc[2,2])
                 E1 = c2.text_input("E1",data_point.iloc[0,3])
                 E2 = c2.text_input("E2",data_point.iloc[1,3])
                 E3 = c2.text_input("E3",data_point.iloc[2,3])
                 H1 = c3.text_input("H1",data_point.iloc[0,4])
                 H2 = c3.text_input("H2",data_point.iloc[1,4])
                 H3 = c3.text_input("H3",data_point.iloc[2,4])
            elif len(data_point)==0:
                 st.warning("ไม่พบชื่อหมุดหลักเขต")
            else:
                 st.dataframe(data=data_point,use_container_width=True)
                 st.warning("จำนวนค่าพิกัดหมุดหลักเขตไม่ครบหรือเกิน 3 ค่า")
        else:
            st.dataframe(data=gdf_postgis_new,use_container_width=True)
            st.warning("โปรดใส่ชื่อหมุดหลักเขต")
    else:
        st.warning("โปรดเลือกวิธีนำเข้า")   
    """
    --------------
    """
    
    image_1 = st.file_uploader("เลือกรูปขณะรับสัญญาณ", accept_multiple_files=False, type=['png', 'jpeg', 'jpg', 'HEIC'],key=f"image_1-{st.session_state.uploader_key}")
    image_2 = st.file_uploader("เลือกรูปหมุดหลักเขต", accept_multiple_files=False, type=['png', 'jpeg', 'jpg', 'HEIC'],key=f"image_2-{st.session_state.uploader_key}")
    image_3 = st.file_uploader("เลือกรูปตำแหน่งรับสัญญาณ", accept_multiple_files=False, type=['png', 'jpeg', 'jpg', 'HEIC'],key=f"image_3-{st.session_state.uploader_key}")
    
    """
    -----------------
    """
    Name_list = df_name_["Name"].to_list()
    Name = st.selectbox("ผู้รังวัด",Name_list)
    f_name = df_name["F_Name-th"][df_name.Name==Name].iloc[0]
    l_name = df_name["L_Name-th"][df_name.Name==Name].iloc[0]
    full_name = "(" + f_name + "  " + l_name + ")"
    Sig = df_name["Signature"][df_name.Name==Name].iloc[0]
    
    date = st.date_input("วันที่ทำการรังวัด",format="DD/MM/YYYY")
    remark = st.text_input("หมายเหตุ","")
    
    
    if sh.title != office_select:
        get_service.clear()
        get_reg.clear()
        creds,gc,service,sh,wks,wks_reg = get_service()
        df_reg = get_reg()
        
    c001, c002 = st.columns([0.12,0.88])
    if c002.button("Refresh", type="primary"):
        st.session_state["Refresh"] = True
        get_service.clear()
        get_reg.clear()
        creds,gc,service,sh,wks,wks_reg = get_service()
        df_reg = get_reg()
    else:
        st.session_state["Refresh"] = False   
    if c001.button("Submit"):
        #import time 
        #start = time.time()
        st.session_state["Submit"] = True
        st.session_state["Login_alert"] = False
        if st.session_state["Search"] == True:
            if N1!="" and N2!="" and N3!="" and E1!="" and E2!="" and E3!="" and N3!="" and E1!="" and E2!="" and E3!="" and H1!="" and H2!=""and H3!="" and parcel_no!="" and survey_no!="" and land_no!="" and UTMMAP1!="" and UTMMAP3!="" and BND_NAME!="" :
                #if sh_report.title != Name+'-Report':
                    #sh_report = gc.open(Name+'-Report_'+office_select)
                N = round((float(N1)+float(N2)+float(N3))/3,3)
                E = round((float(E1)+float(E2)+float(E3))/3,3)
                H = round((float(H1)+float(H2)+float(H3))/3,3)
                if image_1 and image_2 and image_3:
                    image_id = []
                    image = [image_1,image_2,image_3]
                    for i in range(3):
                        image_id.append(upload_image(service,folder_id[i],image[i]))
                    row = [parcel_no, survey_no, province, amphoe, tambon, UTMMAP1, UTMMAP2, UTMMAP3, UTMMAP4, Scale, land_no, Name, round_, Diff, BND_NAME, N, E, H, Method, date.strftime('%d/%m/%Y'), remark, N1, E1, H1, N2, E2, H2, N3, E3, H3,image_id[0],image_id[1],image_id[2]]
                    row_update = wks.append_row(values=row,value_input_option="USER_ENTERED")
                    #gid = row_update['updates']['updatedRange'][5:].split(":")[0]
                    #DATE_temp = wks.acell('S'+gid).value.replace('\xa0',' ').split()
                    #wks.update_acell('AH'+gid,gid)
                    #DATE = DATE_temp[0] + " " + DATE_temp[1] + " " + str(int(DATE_temp[2])+543)
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
            st.warning("โปรดค้นหาข้อมูลในทะเบียน")
    else:
        st.session_state["Submit"] = False
     
#st.session_state         
#else:    
#    st.error("Login failed")
#    st.session_state["Login"] = False
 

