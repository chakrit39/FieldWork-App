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

    # Google Sheets Connection (cached)
    gc = gspread.authorize(creds)
    sh = gc.open(office_select)
    wks = sh.worksheet('Raw')
    
    # Get Registry Data
    wks_reg = sh.worksheet('REG')
    df_reg = pd.DataFrame(wks_reg.get_all_records(numericise_ignore=['all']))

    st.title(f"แบบกรอกข้อมูลภาคสนาม สาขา {office_select}")

    # --- Section 1: Search & Metadata ---
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 2, 2, 1.5, 1.5])
        u1 = c1.text_input("UTMMAP1")
        u2 = c2.selectbox("UTMMAP2", ["I", "II", "III", "IV"])
        u3 = c3.text_input("UTMMAP3")
        scale = c4.selectbox("Scale", sc['SCALE'].unique())
        u4 = c5.selectbox("UTMMAP4", sc[sc['SCALE'] == scale]['UTMMAP4'].unique())
        l_no = c6.text_input("เลขที่ดิน")

        # Auto Search Logic
        utm_key = f"{u1}{u2}{u3}{u4}{scale}{l_no}"
        df_match = df_reg[df_reg['REG_JOIN'] == utm_key].reset_index(drop=True)

        if not df_match.empty:
            col_m1, col_m2 = st.columns(2)
            p_no = col_m1.text_input("เลขที่โฉนด", df_match.at[0, 'PARCEL_NO'])
            s_no = col_m2.text_input("หน้าสำรวจ", df_match.at[0, 'SURVEY_NO'])
            
            col_m3, col_m4, col_m5 = st.columns(3)
            prov = col_m3.text_input("จังหวัด", df_match.at[0, 'PROVINCE'])
            amp = col_m4.text_input("อำเภอ", df_match.at[0, 'AMPHUR'])
            tam = col_m5.text_input("ตำบล", df_match.at[0, 'TAMBOL'])
        else:
            st.warning("โปรดระบุข้อมูลที่ดินให้ถูกต้องเพื่อดึงข้อมูลทะเบียน")
            p_no, s_no, prov, amp, tam = "", "", "", "", ""

    # --- Section 2: Measurement Data ---
    with st.container(border=True):
        cc1, cc2 = st.columns(2)
        bnd_name = cc1.text_input("ชื่อหลักเขต (BND_NAME)")
        method = cc2.selectbox("เครื่องมือการรังวัด", ["RTK GNSS", "Total Station"])
        
        in_method = st.selectbox("วิธีการนำเข้าพิกัด", ["ป้อนค่าพิกัด", "Import from PostGIS"])
        
        coords = {"N": [], "E": [], "H": []}
        chk_diff = False

        if in_method == "ป้อนค่าพิกัด":
            c_n, c_e, c_h = st.columns([4, 4, 2])
            for i in range(1, 4):
                coords["N"].append(c_n.text_input(f"N{i}", key=f"n{i}"))
                coords["E"].append(c_e.text_input(f"E{i}", key=f"e{i}"))
                coords["H"].append(c_h.text_input(f"H{i}", key=f"h{i}"))

        # --- Coordinate Validation ---
        if all(coords["N"]) and all(coords["E"]):
            n_vals = [float(x) for x in coords["N"]]
            e_vals = [float(x) for x in coords["E"]]
            diff_n = max(n_vals) - min(n_vals)
            diff_e = max(e_vals) - min(e_vals)
            
            if diff_n > 0.04 or diff_e > 0.04:
                st.error(f"⚠️ ค่าพิกัดต่างกันเกินเกณฑ์ (N: {diff_n:.3f}, E: {diff_e:.3f})")
            else:
                st.success("✅ ค่าพิกัดอยู่ในเกณฑ์มาตรฐาน")
                chk_diff = True

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
