import os
import time
import json
import queue
import pyaudio
import requests
import firebase_admin
import numpy as np
from firebase_admin import credentials, messaging
from twilio.rest import Client
from vosk import Model, KaldiRecognizer
import subprocess
import re
import geocoder
from geopy.geocoders import Nominatim

# Constants
PANIC_KEYWORDS = ["help", "emergency", "please help", "danger", "fire", "bachao", "sos", "save me"]
COOLDOWN_PERIOD = 10  # seconds
last_alert_time = 0

# Firebase Setup
cred = credentials.Certificate("serviceaccountkey.json")
firebase_admin.initialize_app(cred)

# Twilio Setup
account_sid = ''
auth_token = ''
twilio_client = Client(account_sid, auth_token)

# Smart Lock IFTTT
IFTTT_WEBHOOK_URL = ""

# Load Vosk Model
model_path = "C:/Users/Vishnu kumar/Desktop/intruderalertsystem/aimodels/model/en"
if not os.path.exists(model_path):
    raise Exception("Please download the Vosk model and place it in 'model/en")

model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)

# Audio Stream Setup
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8000)
stream.start_stream()

# Location Fetching
def get_location_string():
    adb_path = r"C:\platform-tools\adb.exe"
    try:
        result = subprocess.run([adb_path, "shell", "dumpsys", "location"], capture_output=True, text=True)
        output = result.stdout
        match = re.search(r'Location\[(gps|fused)\s(-?\d+\.\d+),(-?\d+\.\d+)', output)
        if match:
            lat, lon = match.group(2), match.group(3)
        else:
            g = geocoder.ip('me')
            lat, lon = g.latlng[0], g.latlng[1]

        geolocator = Nominatim(user_agent="panic_alert_location")
        location = geolocator.reverse((lat, lon), language='en')
        address = location.address if location else f"https://maps.google.com/?q={lat},{lon}"
        return f"{address} (https://maps.google.com/?q={lat},{lon})"
    except Exception as e:
        print(f"Location fetch failed: {e}")
        return "Location not available"

# Alert Functions
def send_firebase_notification(location_text):
    message = messaging.Message(
        notification=messaging.Notification(
            title="🚨 Panic Alert!",
            body=f"Immediate assistance required at: {location_text}",
        ),
        topic="panic_alerts",
    )
    response = messaging.send(message)
    print(f"✅ Firebase Notification sent: {response}")

def send_voice_call_alert(location_text):
    twiml = f'<Response><Say voice="alice">Panic alert! Immediate assistance needed at: {location_text}</Say></Response>'
    call = twilio_client.calls.create(
        to="+918056663585", from_="+12165161305", twiml=twiml
    )
    print(f"📞 Call initiated: {call.sid}")

def send_sms_alert(location_text):
    message = twilio_client.messages.create(
        body=f"🚨 Panic alert! Immediate assistance needed at: {location_text}",
        from_="+12165161305",
        to="+918056663585"
    )
    print(f"📩 SMS sent: {message.sid}")

def trigger_smart_lock():
    response = requests.post(IFTTT_WEBHOOK_URL, json={"value1": "lock"})
    print(f"🔒 Smart Lock Triggered: {response.status_code}")

def detect_panic(text):
    return any(keyword in text.lower() for keyword in PANIC_KEYWORDS)

# Real-Time Detection
print("🟢 Listening for panic keywords...")

try:
    while True:
        data = stream.read(4000, exception_on_overflow=False)
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            print("🎙️ You said:", text)
            if detect_panic(text):
                current_time = time.time()
                if current_time - last_alert_time > COOLDOWN_PERIOD:
                    print("🚨 Panic detected! Fetching location and triggering alerts.")
                    last_alert_time = current_time
                    location = get_location_string()
                    send_firebase_notification(location)
                    send_voice_call_alert(location)
                    send_sms_alert(location)
                    trigger_smart_lock()
                else:
                    print("⏳ Cooldown active. Skipping alert.")
except KeyboardInterrupt:
    print("🛑 Stopped.")
finally:
    stream.stop_stream()
    stream.close()
    p.terminate()
