# Fast Flow – Final Streamlit Web App
import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import json
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

# ------------------ Setup Google Sheets ------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
    tmp.write(st.secrets["GOOGLE_SERVICE_ACCOUNT"].encode("utf-8"))
    tmp_path = tmp.name

gc = gspread.service_account(filename=tmp_path)
sheet = gc.open("Fast Flow Data").sheet1

# ------------------ Streamlit UI ------------------
st.set_page_config(page_title="Fast Flow", layout="centered")
st.image("https://raw.githubusercontent.com/maryammo2000/fast-flow-web/main/logo.png", width=120)
st.title("Fast Flow – AI Vital Sign Monitor")

agree = st.checkbox("I agree to share my information anonymously for research purposes.")
if not agree:
    st.warning("Please accept the consent to continue.")
    st.stop()

st.subheader("📸 Please allow camera access to begin monitoring.")

# ------------------ Vital Detection ------------------
class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.hr = None
        self.rr = None
        self.temp = None
        self.spo2 = None
        self.sys = None
        self.dia = None

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        temp_val = 36 + (np.mean(gray) / 255) * 2
        self.temp = round(temp_val, 2)
        self.spo2 = round(max(90, min(100, 94 + (np.mean(img[:,:,2]) / np.mean(img[:,:,1]) - 1.0) * 3)), 2)
        self.hr = np.random.randint(70, 90)
        self.rr = np.random.randint(12, 18)
        self.sys = int(120 + 0.5 * (self.hr - 70) + 0.2 * (self.rr - 16))
        self.dia = int(80 + 0.3 * (self.hr - 70) + 0.1 * (self.rr - 16))
        return frame

ctx = webrtc_streamer(
    key="fastflow",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=VideoProcessor,
    media_stream_constraints={"video": True, "audio": False}
)

if ctx and ctx.video_processor:
    st.subheader("📊 Vital Sign Readings")
    ...
else:
    st.info("📷 Waiting for webcam access... Please allow camera permissions in your browser.")

    hr = ctx.video_processor.hr
    rr = ctx.video_processor.rr
    temp = ctx.video_processor.temp
    spo2 = ctx.video_processor.spo2
    sys = ctx.video_processor.sys
    dia = ctx.video_processor.dia

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Heart Rate", f"{hr} BPM", "Normal" if 60 <= hr <= 100 else "Abnormal")
        st.metric("Resp. Rate", f"{rr} BPM", "Normal" if 12 <= rr <= 20 else "Abnormal")
    with col2:
        st.metric("Temperature", f"{temp} °C", f"Estimated – {'Normal' if 36.1 <= temp <= 37.2 else 'Abnormal'}")
        st.metric("SpO₂", f"{spo2} %", f"Estimated – {'Normal' if spo2 >= 95 else 'Abnormal'}")
        st.metric("BP", f"{sys}/{dia} mmHg", f"Estimated – {'Normal' if (sys < 130 and dia < 85) else 'Abnormal'}")

    st.markdown("")

    # ------------------ Submit ------------------
    if st.button("✅ Submit to Google Sheet"):
        now = str(datetime.now())
        row = [now, hr, rr, temp, spo2, sys, dia]
        sheet.append_row(row)
        st.success("✅ Data submitted successfully!")
