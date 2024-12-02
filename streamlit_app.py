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
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload



#st.markdown("# Work Sheet")
#st.sidebar.header("Work Sheets")

#WorkSheet = st.Page("WorkSheet.py", title="Work Sheet")
#Dashboard = st.Page("Dashboard.py", title="Dashboard")
pg = st.navigation([st.Page("WorkSheet.py"), st.Page("Dashboard.py")])
pg.run()


