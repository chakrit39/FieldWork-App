import streamlit as st
import pandas as pd
import base64
import requests
import gspread
import geopandas as gpd
from sqlalchemy import create_engine
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from PIL import Image
from pillow_heif import register_heif_opener
from io import BytesIO

register_heif_opener()

# --- Config & Const ---
GAS_URL = "https://script.google.com/macros/s/AKfycbwPqmDAj7yPGB4lDIdHtypmfrHgN1CrtI_71OTzcy5lBL9m91-3y3ZiTDUo2A6Gq6cn/exec"
OFFICES = ['ศรีราชา', 'บางละมุง', 'สัตหีบ']
SCOPE = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets',
]

# --- Helper Functions ---

def upload_image_to_gas(image_file, parents, file_metadata):
    """จัดการรูปภาพและส่งไปยัง Google Apps Script"""
    try:
        file_name = f"{file_metadata['prefix']}_{file_metadata['bnd']}.jpeg"
        
        with Image.open(image_file) as img:
            # ปรับขนาดภาพเพื่อประหยัด RAM และ Bandwidth
            img.thumbnail((2000, 2000))
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            img_bytes = BytesIO()
            img.save(img_bytes, format="JPEG", quality=80) # ลด quality เหลือ 80% เพื่อลดขนาดไฟล์
            img_bytes.seek(0)
            b64 = base64.b64encode(img_bytes.read()).decode("utf-8")

        payload = {
            "filename": file_name,
            "mimeType": "image/jpeg",
            "image": b64,
            "parents": parents
        }
        
        # Retry logic
        for _ in range(3):
            r = requests.post(GAS_URL, json=payload, timeout=30)
            res = r.json()
            if res.get("status") == "success":
                return res["fileId"]
        return None
    except Exception as e:
        st.error(f"Image Upload Error: {e}")
        return None

@st.cache_resource(ttl=21600)
def get_creds():
    return ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["dol-mtd5-fieldwork"], SCOPE)

@st.cache_resource(ttl=21600)
def get_postgis_engine():
    s = st.secrets
    return create_engine(f"postgresql://{s['USER']}:{s['PASSWD']}@{s['HOSTNAME']}:5432/Data1")

@st.cache_data(ttl=86400)
def load_static_data():
    sc = pd.read_csv('./UTMMAP4.csv', header=0, dtype={'UTMMAP4': str})
    df_name = pd.read_csv("https://docs.google.com/spreadsheets/d/1taPadBX5zIlk80ZXc7Mn9fW-kK0VT-dgNfCcjRUskgQ/export?gid=0&format=csv")
    df_fol = pd.read_csv("https://docs.google.com/spreadsheets/d/1j0m_zhMDIXrqjsqyRMCczHjm6quwVS4Km0M7WqZ_s2M/export?gid=0&format=csv")
    return sc, df_name, df_fol
    
@st.cache_data(ttl=86400) # แคชไว้ 24 ชั่วโมง
def get_registry_data(office_name):
    """ดึงข้อมูลทะเบียน (REG) และแคชไว้ตามชื่อสำนักงาน"""
    try:
        # ใช้ creds จากฟังก์ชัน get_creds() ที่ทำไว้ก่อนหน้า
        gc = gspread.authorize(get_creds())
        sh = gc.open(office_name)
        wks_reg = sh.worksheet('REG')
        data = wks_reg.get_all_records(numericise_ignore=['all'])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"ไม่สามารถโหลดข้อมูลทะเบียนของ {office_name} ได้: {e}")
        return pd.DataFrame()
# --- Main App ---

st.sidebar.header("Work Sheets")

# Initialize Session States
for key in ["Login", "uploader_key", "Submit"]:
    if key not in st.session_state:
        st.session_state[key] = 0 if key == "uploader_key" else False

if not st.session_state["Login"]:
    with st.form("login_form"):
        st.markdown("#### โปรดเลือก")
        office_select = st.selectbox("สำนักงานที่ดิน", OFFICES)
        round_val = st.selectbox("รอบที่", ["2"])
        if st.form_submit_button("Login"):
            st.session_state["Login"] = True
            st.session_state["office"] = office_select
            st.session_state["round"] = f"รอบที่ {round_val}"
            st.rerun()

else:
    # Load Data
    creds = get_creds()
    sc, df_name, df_fol = load_static_data()
    office_select = st.session_state["office"]
    round_name = st.session_state["round"]

    df_reg = get_registry_data(office_select)

    st.title(f"แบบกรอกข้อมูลภาคสนาม สาขา {office_select}")

# --- Section 1: Search & Metadata ---
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 2, 2, 1.5, 1.5])
        u1 = c1.text_input("UTMMAP1", )
        u2 = c2.selectbox("UTMMAP2", ["I", "II", "III", "IV"])
        u3 = c3.text_input("UTMMAP3", )
        scale = c4.selectbox("Scale", sc['SCALE'].unique())
        u4 = c5.selectbox("UTMMAP4", sc[sc['SCALE'] == scale]['UTMMAP4'].unique())
        l_no = c6.text_input("เลขที่ดิน")

        # --- Logic ค้นหาอัตโนมัติ ---
        # เงื่อนไข: u1, u3 และ l_no ต้องไม่ว่าง
        if u1.strip() != "" and u3.strip() != "" and l_no.strip() != "":
            utm_key = f"{u1}{u2}{u3}{u4}{scale}{l_no}"
            df_match = df_reg[df_reg['REG_JOIN'] == utm_key].reset_index(drop=True)

            if not df_match.empty:
                # กรณีพบข้อมูล: แสดง UI และเติมค่าให้อัตโนมัติ
                col_m1, col_m2 = st.columns(2)
                p_no = col_m1.text_input("เลขที่โฉนด", value=str(df_match.at[0, 'PARCEL_NO']))
                s_no = col_m2.text_input("หน้าสำรวจ", value=str(df_match.at[0, 'SURVEY_NO']))
                
                col_m3, col_m4, col_m5 = st.columns(3)
                prov = col_m3.text_input("จังหวัด", value=df_match.at[0, 'PROVINCE'])
                amp = col_m4.text_input("อำเภอ", value=df_match.at[0, 'AMPHUR'])
                tam = col_m5.text_input("ตำบล", value=df_match.at[0, 'TAMBOL'])
            else:
                # กรณีไม่พบข้อมูล: ให้ผู้ใช้กรอกเองได้ แต่แจ้งเตือนไว้
                st.warning(f"❓ ไม่พบ {utm_key} ในทะเบียน")
        else:
            # กรณีข้อมูลยังไม่ครบ: แสดงช่องว่างรอไว้
            st.info("💡 กรุณากรอกระวางและเลขที่ดินให้ครบ")
            col_m1, col_m2 = st.columns(2)
            p_no = col_m1.text_input("เลขที่โฉนด", value="", disabled=True)
            s_no = col_m2.text_input("หน้าสำรวจ", value="", disabled=True)
            # เติมค่าว่างไว้สำหรับตัวแปรอื่นๆ เพื่อป้องกัน Error ตอน Submit
            prov, amp, tam = "", "", ""
            
    # --- Section 2: Measurement Data ---
    with st.container(border=True):
        def calculate_diffs(pts_df, n_col, e_col):
            diff_n = pts_df[n_col].astype(float).max() - pts_df[n_col].astype(float).min()
            diff_e = pts_df[e_col].astype(float).max() - pts_df[e_col].astype(float).min()
            return round(diff_n, 3), round(diff_e, 3)
    
        cc1, cc2 = st.columns(2)
        BND_NAME = cc1.text_input("ชื่อหลักเขต", "")
        Method = cc2.selectbox("เครื่องมือการรังวัด", ["RTK GNSS", "Total Station"])
        
        chk1, chk2 = st.columns(2)
        upload_method = chk1.selectbox("เลือกวิธีการนำเข้า", ["ป้อนค่าพิกัด", "Upload CSV file", "Import from PostGIS"])
        Diff_Limit = 0.04  # ตั้งค่าเกณฑ์มาตรฐานไว้ที่นี่
        chk_diff = False
        
        # ตัวแปรสำหรับเก็บข้อมูลพิกัดที่จะนำไปใช้งานต่อ
        final_pts = None
    
        # --- ส่วนการนำเข้าข้อมูล ---
        if upload_method == "ป้อนค่าพิกัด":
            c1, c2, c3 = st.columns([0.4, 0.4, 0.2])
            N1, N2, N3 = [c1.text_input(f"N{i}", key=f"N{i}") for i in range(1, 4)]
            E1, E2, E3 = [c2.text_input(f"E{i}", key=f"E{i}") for i in range(1, 4)]
            H1, H2, H3 = [c3.text_input(f"H{i}", key=f"H{i}") for i in range(1, 4)]
            
            if all([N1, N2, N3, E1, E2, E3, H1, H2, H3]):
                final_pts = pd.DataFrame({
                    'N': [N1, N2, N3], 'E': [E1, E2, E3], 'H': [H1, H2, H3]
                })
    
        elif upload_method == "Upload CSV file":
            no_header = chk1.checkbox("ไม่มี Header")
            file = st.file_uploader("เลือกไฟล์ CSV", type=['csv'])
            if file and BND_NAME:
                df_csv = pd.read_csv(file, header=None if no_header else 0)
                if no_header:
                    df_csv.columns = ["Name", "Code", "N", "E", "h"]
                
                data_point = df_csv[df_csv['Code'] == BND_NAME].reset_index(drop=True)
                if len(data_point) == 3:
                    st.dataframe(data_point, use_container_width=True)
                    final_pts = data_point.rename(columns={'h': 'H'})[['N', 'E', 'H']]
                else:
                    st.warning(f"พบข้อมูล {len(data_point)} จุด (ต้องใช้ 3 จุด)")
    
        elif upload_method == "Import from PostGIS":
            offices_map = {"ศรีราชา": "SRIRACHA", "บางละมุง": "BANGLAMUNG", "สัตหีบ": "SATTAHIP"} # ขยายต่อได้
            off_eng = offices_map.get(office_select)
            if BND_NAME and off_eng:
                sql = f"SELECT \"Name\", \"Code\", \"N\", \"E\", \"h\" FROM \"public\".\"BND_{off_eng}\" WHERE \"Code\" = '{BND_NAME}'"
                data_db = gpd.read_postgis(sql, engine, geom_col=None) # หรือใช้ pd.read_sql
                if len(data_db) == 3:
                    st.dataframe(data_db, use_container_width=True)
                    final_pts = data_db.rename(columns={'h': 'H'})[['N', 'E', 'H']]
                else:
                    st.warning(f"พบข้อมูลในระบบ {len(data_db)} จุด")
            
    # --- Section 3: Photos ---
    with st.container(border=True):
        st.subheader("อัปโหลดรูปภาพ")
        img_keys = [f"img_{i}_{st.session_state.uploader_key}" for i in range(3)]
        up_imgs = [st.file_uploader(f"รูปที่ {i+1}", type=['jpg','jpeg','png','heic'], key=k) for i, k in enumerate(img_keys)]

    # --- Section 4: Surveyor & Submit ---
    surveyor = st.selectbox("ผู้รังวัด", df_name[df_name[round_name]==True]["Name"])
    obs_date = st.date_input("วันที่รังวัด", format="DD/MM/YYYY")
    remark = st.text_input("หมายเหตุ")

    if st.button("Submit Data", type="primary"):
        if not all(up_imgs):
            st.error("โปรดอัปโหลดรูปภาพให้ครบ 3 รูป")
        elif not chk_diff:
            st.error("ค่าพิกัดไม่ผ่านเกณฑ์หรือกรอกข้อมูลไม่ครบ")
        else:
            with st.spinner("กำลังบันทึกข้อมูลและอัปโหลดรูปภาพ..."):
                # 1. Upload Images
                df_fol_office = df_fol[df_fol.Name == office_select].iloc[0]
                folder_ids = [df_fol_office['Folder1'], df_fol_office['Folder2'], df_fol_office['Folder3']]
                
                meta = {"prefix": f"{u1}{u2}{u3}-{u4}-{scale}-{l_no}", "bnd": bnd_name}
                img_ids = []
                for img_file, f_id in zip(up_imgs, folder_ids):
                    fid = upload_image_to_gas(img_file, f_id, meta)
                    img_ids.append(fid)

                if None not in img_ids:
                    # 2. Prepare Row Data
                    avg_n = round(sum([float(x) for x in coords["N"]])/3, 3)
                    avg_e = round(sum([float(x) for x in coords["E"]])/3, 3)
                    avg_h = round(sum([float(x) for x in coords["H"]])/3, 3)
                    
                    final_row = [
                        p_no, s_no, prov, amp, tam, u1, u2, u3, u4, scale, l_no,
                        surveyor, round_name, "", bnd_name, avg_n, avg_e, avg_h, 
                        method, obs_date.strftime('%d/%m/%Y'), remark
                    ] + coords["N"] + coords["E"] + coords["H"] + img_ids
                    
                    wks.append_row(final_row, value_input_option="USER_ENTERED")
                    
                    st.success("บันทึกข้อมูลสำเร็จ!")
                    st.session_state.uploader_key += 1 # Reset uploader
                    st.rerun()
                else:
                    st.error("การอัปโหลดรูปภาพล้มเหลว โปรดลองอีกครั้ง")
