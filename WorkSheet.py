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

st.set_page_config(page_title="WorkSheet")

st.sidebar.header("Work Sheets")
st.sidebar.markdown("แอปพลิเคชันสร้างรายงานจากข้อมูลภาคสนาม")

if "Submit" not in st.session_state:
    st.session_state["Submit"] = False
if "submit_office" not in st.session_state:
    st.session_state["submit_office"] = False
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
    temp_file = open(path, 'wb')
    temp_file.write(image_i.getvalue())
    temp_file.close()
    file_metadata = {"name": file_name,"parents": [parents]}
    media = MediaFileUpload(path, mimetype="image/jpeg")
    file = (service.files().create(body=file_metadata, media_body=media, fields="id").execute() )
    file_id = file['id']
    del media
    del file
    del file_metadata
    os.remove(path)
    return file_id
def create_report():
    List = []
    for i_wks in sh_report.worksheets():
        List.append(i_wks.title)
    count = List.count(BND_NAME)
    if count == 0:
        BND_NAME_ = BND_NAME
    else:
        new = count+1
        while count != 0:
            BND_NAME_ = BND_NAME + "_" + str(new)
            count = List.count(BND_NAME_)
            new += 1
    copiedSheet = wks_ref.copy_to(sh_report.id)
    dstSheet = sh_report.worksheet(copiedSheet['title'])
    dstSheet.update_title(BND_NAME_)
    dstSheet.update([[BND_NAME],[parcel_no],[UTMMAP1+" "+UTMMAP2+" "+UTMMAP3+"-"+UTMMAP4],[tambon]], 'H4:H7',value_input_option="USER_ENTERED")
    dstSheet.update_acell('S6',"1 : " + str(Scale))
    dstSheet.update_acell('S7',amphoe)
    dstSheet.update([[DATE],[survey_no],[land_no],[province]], 'AF4:AF7',value_input_option="USER_ENTERED")
    
    #dstSheet.update_acell('H4',BND_NAME)
    #dstSheet.update_acell('H6',UTMMAP1+" "+UTMMAP2+" "+UTMMAP3+"-"+UTMMAP4)
    #dstSheet.update_acell('O6',"1 : " + str(Scale))
    #dstSheet.update_acell('AF6',LANDNO)
    #dstSheet.update_acell('H5',PARCEL_NO)
    #dstSheet.update_acell('AF5',SURVEY_NO)
    #dstSheet.update_acell('H7',tambon)
    #dstSheet.update_acell('S7',amphoe)
    #dstSheet.update_acell('AF7',province)
    #dstSheet.update_acell('AF4',DATE)
    dstSheet.update_acell('K39',N)
    dstSheet.update_acell('U39',E)
    dstSheet.update_acell('AE39',H)
    dstSheet.update_acell('F40',remark)
    dstSheet.update_acell('Y43',full_name)
    dstSheet.update([[N1],[N2],[N3]], 'K34:K36', value_input_option="USER_ENTERED")
    dstSheet.update([[E1],[E2],[E3]], 'U34:UE36', value_input_option="USER_ENTERED")
    dstSheet.update([[H1],[H2],[H3]], 'AE34:AE36', value_input_option="USER_ENTERED")
    dstSheet.update('A11', [['=image("https://drive.google.com/uc?export=download&id=' + image_id[0] + '")']], value_input_option="USER_ENTERED")
    dstSheet.update('U11', [['=image("https://drive.google.com/uc?export=download&id=' + image_id[1] + '")']], value_input_option="USER_ENTERED")
    dstSheet.update('K22', [['=image("https://drive.google.com/uc?export=download&id=' + image_id[2] + '")']], value_input_option="USER_ENTERED")
    dstSheet.update('Y40', [['=image("https://drive.google.com/uc?export=download&id=' + Sig + '")']], value_input_option="USER_ENTERED")
    #body = {
    #  "requests": [
    #      {
    #          "copyPaste": {
    #              "source": {
    #                  "sheetId": dstSheet.id,
    #                  "startRowIndex": 10,
    #                  "endRowIndex": 44,
    #                  "startColumnIndex": 0,
    #                  "endColumnIndex": 39
    #              },
    #              "destination": {
    #                  "sheetId": dstSheet.id,
    #                  "startRowIndex": 10,
    #                  "endRowIndex": 44,
    #                  "startColumnIndex": 0,
    #                  "endColumnIndex": 39
    #              },
    #              "pasteType": "PASTE_VALUES"
    #                        }
    #      }
    #               ]
    #        }
    #res = sh_report.batch_update(body)
    
@st.cache_resource 
def get_service():
    #if "creds" not in globals() :
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["dol-mtd5-fieldwork"], scope)
    gc = gspread.authorize(creds)
    service = build("drive", "v3", credentials=creds)
    sh = gc.open(office_select)
    wks = sh.worksheet('Raw')
    sh_ref = gc.open('Report') 
    wks_ref = sh_ref.worksheet('Ref')
    sh_report = gc.open(Name+'-Report_'+office_select)
    return creds,gc,service,sh,wks,sh_ref,wks_ref,sh_report
    
@st.cache_resource 
def get_postgis():
    HOSTNAME = st.secrets["HOSTNAME"]
    USER = st.secrets["USER"]
    PASSWD = st.secrets["PASSWD"]
    engine = create_engine( f"postgresql://{USER}:{PASSWD}@{HOSTNAME}:7001/Data1")
    return engine
    
@st.cache_data
def get_data():
    df = pd.read_csv('./ONGKHARAK.csv',header=0)
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
        
Office = ['องครักษ์','ลำลูกกา']        
placeholder = st.empty()
with placeholder.form("login"):
    st.markdown("#### โปรดเลือก")
    office_select = st.selectbox("สำนักงานที่ดิน",Office)
    round = st.selectbox("รอบที่",["1","2"])
    submit_office = st.form_submit_button("Login")
    if submit_office:
        st.session_state["Login"] = True
    else:
        st.session_state["Login"] = False
    #placeholder_check = placeholder
if st.session_state["Login"]:
    office_select = office_select
    round = "รอบที่" + round
    placeholder.empty()
    #placeholder_check = placeholder
    st.success("Login successful")
    
    df,sc,df_name,df_fol = get_data()
    engine = get_postgis()
    df_fol[df_fol.Name==office_select]
    folder_id = []
    
    st.title("แบบกรอกข้อมูลงานภาคสนาม")
    st.title("สาขา"+office_select)  
    
    c01, c02, c03 = st.columns([0.35,0.35,0.3])
    parcel_no = c01.text_input("เลขที่โฉนด","")
    survey_no = c02.text_input("หน้าสำรวจ","")
    land_no = c03.text_input("เลขที่ดิน","")
    
    col_1, col_2, col_3, col_4, col_5 = st.columns([0.2,0.2,0.2,0.2,0.2])
    UTMMAP1 = col_1.text_input("UTMMAP1","")
    UTMMAP2 = col_2.selectbox("UTMMAP2",["I", "II", "III", "IV"],)
    UTMMAP3 = col_3.text_input("UTMMAP3","")
    Scale = col_4.selectbox("Scale",pd.unique(sc.SCALE),)
    UTMMAP4 = col_5.selectbox("UTMMAP4",pd.unique(sc.UTMMAP4[sc.SCALE==Scale]),)
    
    col1, col2, col3 = st.columns([0.35,0.35,0.3])
    province = col1.selectbox("จังหวัด",pd.unique(df.P_NAME_T))
    amphoe = col2.selectbox("อำเภอ",pd.unique(df.A_NAME_T[df.P_NAME_T==province]))
    tambon = col3.selectbox("ตำบล",pd.unique(df.T_NAME_T[df.A_NAME_T==amphoe]))
    
    """
    --------------
    """
    cc1, cc2 = st.columns([0.5,0.5])
    BND_NAME = cc1.text_input("ชื่อหลักเขต","")
    Method = cc2.selectbox("เครื่องมือการรังวัด",["RTK GNSS","Total Station"])
    chk1, chk2 = st.columns([0.5,0.5])
    upload_method = chk1.selectbox("เลือกวิธีการนำเข้า",["ป้อนค่าพิกัด","Upload a CSV file (Name,Code,N,E,h)","Import from PostGIS"])
    
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
                    #st.dataframe(data=data_point,use_container_width=False)
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
                    st.warning("จำนวนค่าพิกัดหมุดหลักเขตไม่ครบหรือเกิน 3 ค่า")
            else:
                st.warning("โปรดใส่ชื่อหมุดหลักเขต")
    elif upload_method == "Import from PostGIS":
        sql = f'SELECT * FROM "public"."BND_Points"'
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
    Name_list = df_name["Name"].to_list()
    Name = st.selectbox("ผู้รังวัด",Name_list)
    f_name = df_name["F_Name-th"][df_name.Name==Name].iloc[0]
    l_name = df_name["L_Name-th"][df_name.Name==Name].iloc[0]
    full_name = "(" + f_name + "  " + l_name + ")"
    Sig = df_name["Signature"][df_name.Name==Name].iloc[0]
    
    date = st.date_input("วันที่ทำการรังวัด",format="DD/MM/YYYY")
    remark = st.text_input("หมายเหตุ","")
    
    creds,gc,service,sh,wks,sh_ref,wks_ref,sh_report = get_service()
    c001, c002 = st.columns([0.12,0.88])
    
    if c002.button("Refresh", type="primary"):
        st.session_state["Refresh"] = True
        get_service.clear()
        creds,gc,service,sh,wks,sh_ref,wks_ref,sh_report = get_service()
    else:
        st.session_state["Refresh"] = False   
        
    if c001.button("Submit"):
        #import time 
        #start = time.time()
        st.session_state["Submit"] = True
        if N1!="" and N2!="" and N3!="" and E1!="" and E2!="" and E3!="" and N3!="" and E1!="" and E2!="" and E3!="" and H1!="" and H2!=""and H3!="" and parcel_no!="" and survey_no!="" and land_no!="" and UTMMAP1!="" and UTMMAP3!="" and BND_NAME!="" :
            if sh_report.title != Name+'-Report':
                sh_report = gc.open(Name+'-Report_'+office_select)
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
     
st.session_state         
#else:    
#    st.error("Login failed")
#    st.session_state["Login"] = False
 

