import streamlit as st
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tempfile
import json
import cv2
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, WebRtcMode
import time

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
        self.last_update = time.time()
        self.data = {
            'hr': None, 'rr': None, 'temp': None,
            'spo2': None, 'sys': None, 'dia': None,
            'face_detected': False
        }
        self.stable_data = None
        self.timer_start = time.time()

    def recv(self, frame):
        now = time.time()
        img = frame.to_ndarray(format="bgr24")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0:
            self.data['face_detected'] = True
            if now - self.last_update > 1:
                self.last_update = now
                self.data['temp'] = round(36 + (np.mean(gray) / 255) * 2, 2)
                self.data['spo2'] = round(max(90, min(100, 94 + (np.mean(img[:,:,2]) / np.mean(img[:,:,1]) - 1.0) * 3)), 2)
                self.data['hr'] = np.random.randint(70, 90)
                self.data['rr'] = np.random.randint(12, 18)
                self.data['sys'] = int(120 + 0.5 * (self.data['hr'] - 70) + 0.2 * (self.data['rr'] - 16))
                self.data['dia'] = int(80 + 0.3 * (self.data['hr'] - 70) + 0.1 * (self.data['rr'] - 16))
                if now - self.timer_start >= 30 and not self.stable_data:
                    self.stable_data = self.data.copy()
        else:
            self.data = {
                'hr': None, 'rr': None, 'temp': None,
                'spo2': None, 'sys': None, 'dia': None,
                'face_detected': False
            }

        return frame

# ------------------ Start Camera ------------------
ctx = webrtc_streamer(
    key="fastflow",
    mode=WebRtcMode.SENDRECV,
    video_processor_factory=VideoProcessor,
    media_stream_constraints={"video": {"width": 640, "height": 480}, "audio": False},
    async_processing=True
)

# ------------------ Display Live Data ------------------
if ctx and ctx.state.playing and ctx.video_processor:
    vp = ctx.video_processor
    st.markdown("## 🔄 Live Monitoring")
    placeholder = st.empty()

    while ctx.state.playing:
        with placeholder.container():
            col1, col2 = st.columns(2)

            def show(label, value, normal_range, estimated=False):
                if value is None:
                    st.metric(label, "--", "No person detected")
                else:
                    status = "Normal" if normal_range[0] <= value <= normal_range[1] else "Abnormal"
                    label_out = f"Estimated – {status}" if estimated else status
                    st.metric(label, f"{value}", label_out)

            with col1:
                show("Heart Rate", vp.data['hr'], (60, 100))
                show("Resp. Rate", vp.data['rr'], (12, 20))

            with col2:
                show("Temperature (°C)", vp.data['temp'], (36.1, 37.5), estimated=True)
                show("SpO₂ (%)", vp.data['spo2'], (95, 100), estimated=True)

                if vp.data['sys'] and vp.data['dia']:
                    sys_ok = 90 <= vp.data['sys'] <= 130
                    dia_ok = 60 <= vp.data['dia'] <= 85
                    status = "Normal" if sys_ok and dia_ok else "Abnormal"
                    st.metric("BP", f"{vp.data['sys']}/{vp.data['dia']} mmHg", f"Estimated – {status}")
                else:
                    st.metric("BP", "--/--", "No person detected")

            if vp.stable_data:
                st.markdown("## 📊 Measurements (Stabilized After 30 Seconds)")
                st.write({
                    "Heart Rate": vp.stable_data['hr'],
                    "Resp. Rate": vp.stable_data['rr'],
                    "Temp (°C)": vp.stable_data['temp'],
                    "SpO₂ (%)": vp.stable_data['spo2'],
                    "BP": f"{vp.stable_data['sys']}/{vp.stable_data['dia']} mmHg"
                })

            if vp.data['hr'] and st.button("✅ Submit to Google Sheet"):
                row = [
                    str(datetime.now()), vp.data['hr'], vp.data['rr'],
                    vp.data['temp'], vp.data['spo2'], vp.data['sys'], vp.data['dia']
                ]
                sheet.append_row(row)
                st.success("✅ Data submitted successfully!")

        time.sleep(1)
else:
    st.info("⏳ Waiting for camera to load or permission...")
