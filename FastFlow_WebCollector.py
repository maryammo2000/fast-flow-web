# Fast Flow Web Collector – Updated JSON filename
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Use the correct service account file
gc = gspread.service_account(filename="fastflowcollector-a570a2dfbf0f.json")
sheet = gc.open("Fast Flow Data").sheet1

# App title and logo
st.set_page_config(page_title="Fast Flow Vital Sign Collector", page_icon="🩺", layout="centered")
st.image("https://raw.githubusercontent.com/maryammo2000/fast-flow-web/main/logo.png", width=120)
st.title("Fast Flow – Vital Sign Collection")

# Consent
agree = st.checkbox("I agree to share my information anonymously for research purposes.")
if not agree:
    st.warning("Please accept the consent to continue.")
    st.stop()

# Input fields
col1, col2 = st.columns(2)
with col1:
    age = st.number_input("Age", min_value=1, max_value=120)
    gender = st.selectbox("Gender", ["Female", "Male"])
with col2:
    hr = st.number_input("Heart Rate (BPM)", min_value=30, max_value=200)
    rr = st.number_input("Respiratory Rate (BPM)", min_value=5, max_value=40)

spo2 = st.slider("SpO₂ (%)", 70, 100, 98)
temp = st.slider("Temperature (°C)", 34, 42, 37)
bp_sys = st.number_input("Systolic BP (mmHg)", min_value=70, max_value=200)
bp_dia = st.number_input("Diastolic BP (mmHg)", min_value=40, max_value=130)

# Submit
if st.button("Submit Data"):
    row = [str(datetime.now()), age, gender, hr, rr, spo2, temp, bp_sys, bp_dia]
    sheet.append_row(row)
    st.success("✅ Thank you! Your data has been recorded anonymously.")
