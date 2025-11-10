import streamlit as st


#st.markdown("# Work Sheet")
#st.sidebar.header("Work Sheets")

#WorkSheet = st.Page("WorkSheet.py", title="Work Sheet")
#Dashboard = st.Page("Dashboard.py", title="Dashboard")
pg = st.navigation([st.Page("WorkSheet.py"), st.Page("CSV2Postgres.py"), st.Page("Dashboard.py"), st.Page("Query.py")])
pg.run()


