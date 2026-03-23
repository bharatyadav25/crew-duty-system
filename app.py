import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets connection
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/drive"]

creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

sheet = client.open("CrewData").sheet1

st.title("Crew Night Duty System")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, header=2)
    df['DateTime'] = pd.to_datetime(df['DateTime'], dayfirst=True)

    # Remove duplicates
    df = df.drop_duplicates()

    # Upload to sheet
    sheet.append_rows(df.values.tolist())

    st.success("Data Uploaded Successfully ✅")