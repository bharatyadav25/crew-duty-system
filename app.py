import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- GOOGLE SHEETS CONNECT ----------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# ✅ Direct secrets dict use (NO json.loads)
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["GOOGLE_CREDENTIALS"], scope
)

client = gspread.authorize(creds)
sheet = client.open("CrewData").sheet1

# ---------- UI ----------
st.title("🚆 Crew Night Duty System (Final)")

uploaded_file = st.file_uploader("📤 Upload Excel File", type=["xlsx"])

# ---------- PROCESS ----------
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, header=2)
        df['DateTime'] = pd.to_datetime(df['DateTime'], dayfirst=True)

        # Remove duplicates
        df = df.drop_duplicates()

        st.subheader("📊 Uploaded Data Preview")
        st.dataframe(df.head())

        # Upload to Google Sheet
        sheet.append_rows(df.values.tolist())
        st.success("✅ Data Uploaded to Google Sheets")

        # ---------- SIGNON-SIGNOFF PAIR ----------
        df = df.sort_values(['Crew Id', 'DateTime'])

        records = []

        for crew_id, group in df.groupby('Crew Id'):
            sign_on = None
            crew_name = None

            for _, row in group.iterrows():
                if row['Action'] == 'SIGNON':
                    sign_on = row['DateTime']
                    crew_name = row['Crew Name']

                elif row['Action'] == 'SIGNOFF' and sign_on is not None:
                    records.append({
                        'Crew Id': row['Crew Id'],
                        'Crew Name': crew_name,
                        'SignOn': sign_on,
                        'SignOff': row['DateTime']
                    })
                    sign_on = None

        duty_df = pd.DataFrame(records)

        # ---------- NIGHT CHECK ----------
        def is_night(sign_on, sign_off):
            if sign_off.date() > sign_on.date():
                return True
            return not (sign_on.hour > 5 and sign_off.hour > 5)

        duty_df['Night'] = duty_df.apply(
            lambda x: is_night(x['SignOn'], x['SignOff']), axis=1
        )

        night_df = duty_df[duty_df['Night'] == True].copy()
        night_df['Date'] = night_df['SignOn'].dt.date

        # ---------- STREAK LOGIC ----------
        night_df = night_df.sort_values(['Crew Id', 'Date'])

        final_rows = []

        for crew_id, group in night_df.groupby('Crew Id'):
            group = group.sort_values('Date')
            streak = []

            for i in range(len(group)):
                if not streak:
                    streak.append(group.iloc[i])
                else:
                    prev = streak[-1]['Date']
                    curr = group.iloc[i]['Date']

                    if (curr - prev).days == 1:
                        streak.append(group.iloc[i])
                    else:
                        if len(streak) >= 3:
                            for idx, row in enumerate(streak):
                                day_num = idx + 1
                                if 3 <= day_num <= 6:
                                    final_rows.append({
                                        'Crew Id': row['Crew Id'],
                                        'Crew Name': row['Crew Name'],
                                        'Day': f"{day_num}th day",
                                        'Date': row['Date']
                                    })
                        streak = [group.iloc[i]]

            if len(streak) >= 3:
                for idx, row in enumerate(streak):
                    day_num = idx + 1
                    if 3 <= day_num <= 6:
                        final_rows.append({
                            'Crew Id': row['Crew Id'],
                            'Crew Name': row['Crew Name'],
                            'Day': f"{day_num}th day",
                            'Date': row['Date']
                        })

        final_df = pd.DataFrame(final_rows)

        # ---------- FINAL REPORT ----------
        if not final_df.empty:
            pivot_df = final_df.pivot_table(
                index=['Crew Id', 'Crew Name'],
                columns='Day',
                values='Date',
                aggfunc='first'
            ).reset_index()

            st.subheader("📊 Final Report (3–6 Day Streak)")
            st.dataframe(pivot_df)

            # Download button
            csv = pivot_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Download Report",
                data=csv,
                file_name="final_report.csv",
                mime="text/csv"
            )

        else:
            st.warning("⚠️ No 3–6 day night duty streak found")

        st.success("🎯 Processing Complete")

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
