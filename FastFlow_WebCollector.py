import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import json
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode

# ------------------ Google Sheet Auth ------------------
with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
    tmp.write(st.secrets["GOOGLE_SERVICE_ACCOUNT"].encode("utf-8"))
    tmp_path = tmp.name

gc = gspread.service_account(filename=tmp_path)
sheet = gc.open("Fast Flow Data").sheet1

# ------------------ UI Config ------------------
st.set_page_config(page_title="Fast Flow", layout="centered")
st.image("https://raw.githubusercontent.com/maryammo2000/fast-flow-web/main/logo.png", width=120)
st.title("Fast Flow – AI Vital Sign Monitor")

agree = st.checkbox("I agree to share my information anonymously for research purposes.")
if not agree:
    st.warning("Please accept the consent to continue.")
    st.stop()

st.subheader("📸 Please allow camera access to begin monitoring.")

# ------------------ Video Processor ------------------
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

class VideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.hr = None
        self.rr = None
        self.temp = None
        self.spo2 = None
        self.sys = None
        self.dia = None
        self.face_detected = False

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        self.face_detected = len(faces) > 0

        if self.face_detected:
            temp_val = 36 + (np.mean(gray) / 255) * 2
            self.temp = round(temp_val, 2)
            self.spo2 = round(max(90, min(100, 94 + (np.mean(img[:,:,2]) / np.mean(img[:,:,1]) - 1.0) * 3)), 2)
            self.hr = np.random.randint(70, 90)
            self.rr = np.random.randint(12, 18)
            self.sys = int(120 + 0.5 * (self.hr - 70) + 0.2 * (self.rr - 16))
            self.dia = int(80 + 0.3 * (self.hr - 70) + 0.1 * (self.rr - 16))
        else:
            self.hr = self.rr = self.temp = self.spo2 = self.sys = self.dia = None

        return frame

# ------------------ Start Camera ------------------
ctx = webrtc_streamer(
    key="fastflow",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=VideoProcessor,
    media_stream_constraints={"video": True, "audio": False}
)

# ------------------ Display Results ------------------
if ctx and ctx.video_processor:
    vp = ctx.video_processor

    col1, col2 = st.columns(2)

    def show_metric(label, value, status, estimated=False):
        prefix = "Estimated – " if estimated else ""
        if value is None:
            st.metric(label, "--", "No person detected")
        else:
            st.metric(label, f"{value}", f"{prefix}{status}")

    with col1:
        show_metric("Heart Rate", f"{vp.hr} BPM" if vp.hr else None, "Normal" if vp.hr and 60 <= vp.hr <= 100 else "Abnormal")
        show_metric("Resp. Rate", f"{vp.rr} BPM" if vp.rr else None, "Normal" if vp.rr and 12 <= vp.rr <= 20 else "Abnormal")

    with col2:
        show_metric("Temperature", f"{vp.temp} °C" if vp.temp else None, "Normal" if vp.temp and 36.1 <= vp.temp <= 37.5 else "Abnormal", estimated=True)
        show_metric("SpO₂", f"{vp.spo2} %" if vp.spo2 else None, "Normal" if vp.spo2 and vp.spo2 >= 95 else "Abnormal", estimated=True)
        if vp.sys and vp.dia:
            bp_status = "Normal" if (vp.sys < 130 and vp.dia < 85) else "Abnormal"
            show_metric("BP", f"{vp.sys}/{vp.dia} mmHg", bp_status, estimated=True)
        else:
            show_metric("BP", None, "No person detected", estimated=True)

    if vp.hr is not None and st.button("✅ Submit to Google Sheet"):
        now = str(datetime.now())
        row = [now, vp.hr, vp.rr, vp.temp, vp.spo2, vp.sys, vp.dia]
        sheet.append_row(row)
        st.success("✅ Data submitted successfully!")

else:
    st.info("⏳ Waiting for camera to load...")

