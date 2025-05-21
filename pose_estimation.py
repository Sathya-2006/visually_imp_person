import cv2
import mediapipe as mp
import time
import pygame
import firebase_admin
from firebase_admin import credentials, db
from twilio.rest import Client
import threading
import traceback
import subprocess
import re
import geocoder
from geopy.geocoders import Nominatim
import qrcode

# ====== Firebase Initialization ======
cred = credentials.Certificate("serviceaccountkey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': ''
})

# ====== Twilio Setup ======
twilio_sid = ''
twilio_token = ''
twilio_from = '+12165161305'
twilio_to = '+918056663585'
twilio_client = Client(twilio_sid, twilio_token)

# ====== Alarm Sound Setup ======
pygame.mixer.init()
pygame.mixer.music.load("alarm.mp3")

# ====== MediaPipe Pose Setup ======
mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

# ====== Camera Setup ======
cap = cv2.VideoCapture(0)

# ====== State Variables ======
pose_start_times = {'hands_up': None, 'crouch': None}
pose_held_flags = {'hands_up': False, 'crouch': False}
cooldown_active = False

# ====== Location Fetcher ======
def get_location():
    adb_path = r"C:\platform-tools\adb.exe"  # Change if needed

    try:
        result = subprocess.run([adb_path, "shell", "dumpsys", "location"], capture_output=True, text=True)
        output = result.stdout
        match = re.search(r'Location\[(gps|fused)\s(-?\d+\.\d+),(-?\d+\.\d+)', output)

        if match:
            lat = match.group(2)
            lon = match.group(3)
            return lat, lon
        else:
            g = geocoder.ip('me')
            if g.latlng:
                lat, lon = g.latlng
                return str(lat), str(lon)
            else:
                return None, None
    except:
        return None, None

# ====== QR Code Generator (optional) ======
def generate_qr(lat, lon):
    if lat and lon:
        url = f"https://maps.google.com/?q={lat},{lon}"
        qr = qrcode.make(url)
        qr.save("location_qr.png")

# ====== Alert Sender ======
def send_alert(message="Emergency Alert Triggered!"):
    try:
        lat, lon = get_location()
        location_url = ""
        if lat and lon:
            location_url = f"\n📍 Location: https://maps.google.com/?q={lat},{lon}"
            generate_qr(lat, lon)

        full_message = f"{message}{location_url}"

        print("✅ Pushing alert to Firebase...")
        db.reference('alerts').push({
            'timestamp': str(time.ctime()),
            'message': full_message
        })

        print("📩 Sending SMS...")
        sms = twilio_client.messages.create(
            body=f"🚨 Alert: {full_message}",
            from_=twilio_from,
            to=twilio_to
        )
        print("📩 SMS sent:", sms.sid)

        print("📞 Initiating call...")
        call = twilio_client.calls.create(
            twiml=f'<Response><Say>{message}</Say></Response>',
            from_=twilio_from,
            to=twilio_to
        )
        print("📞 Call initiated:", call.sid)

        pygame.mixer.music.play()

    except Exception as e:
        print("❌ Alert Error:", str(e))
        traceback.print_exc()

# ====== Cooldown Control ======
def activate_cooldown(duration=3):
    global cooldown_active
    cooldown_active = True
    print("⏳ Cooldown activated...")
    threading.Timer(duration, reset_cooldown).start()

def reset_cooldown():
    global cooldown_active
    cooldown_active = False
    print("✅ Cooldown ended.")

def is_cooldown_active():
    return cooldown_active

# ====== Main Loop ======
print("📹 Starting pose detection. Press ESC to exit.")

try:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            print("❌ Camera error.")
            break

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        current_time = time.time()

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

            visibility_ok = all(
                landmarks[i].visibility > 0.5 for i in [
                    mp_pose.PoseLandmark.LEFT_WRIST.value,
                    mp_pose.PoseLandmark.RIGHT_WRIST.value,
                    mp_pose.PoseLandmark.NOSE.value
                ]
            )

            if visibility_ok and not is_cooldown_active():
                left_hand = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]
                right_hand = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                nose = landmarks[mp_pose.PoseLandmark.NOSE.value]

                if left_hand.y < nose.y and right_hand.y < nose.y:
                    print("🙌 Hands-up detected!")

                    if pose_start_times['hands_up'] is None:
                        pose_start_times['hands_up'] = current_time
                        print("⏳ Holding hands-up pose...")

                    elif not pose_held_flags['hands_up'] and current_time - pose_start_times['hands_up'] >= 5:
                        pose_held_flags['hands_up'] = True
                        print("✅ Pose held. Sending hands-up alert...")
                        send_alert("Hands-up pose detected!")
                        activate_cooldown()

                else:
                    pose_start_times['hands_up'] = None
                    pose_held_flags['hands_up'] = False

                l_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP.value]
                r_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP.value]
                l_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value]
                r_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE.value]

                avg_hip_y = (l_hip.y + r_hip.y) / 2
                avg_knee_y = (l_knee.y + r_knee.y) / 2

                if avg_hip_y > 0.55 and avg_knee_y > 0.7 and avg_knee_y < avg_hip_y:
                    print("🔻 Crouching detected!")

                    if pose_start_times['crouch'] is None:
                        pose_start_times['crouch'] = current_time
                        print("⏳ Holding crouch pose...")

                    elif not pose_held_flags['crouch'] and current_time - pose_start_times['crouch'] >= 5:
                        pose_held_flags['crouch'] = True
                        print("✅ Pose held. Sending crouch alert...")
                        send_alert("Crouching pose detected!")
                        activate_cooldown()

                else:
                    pose_start_times['crouch'] = None
                    pose_held_flags['crouch'] = False

                l_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
                r_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
                avg_shoulder_y = (l_shoulder.y + r_shoulder.y) / 2

                if abs(avg_hip_y - avg_shoulder_y) < 0.1:
                    print("🛏️ Lying down detected!")
                    if not is_cooldown_active():
                        send_alert("Lying down pose detected!")
                        activate_cooldown()

        cv2.imshow("Pose Detection", image)
        if cv2.waitKey(5) & 0xFF == 27:
            print("👋 Exiting...")
            break

except Exception as e:
    print("❌ Fatal error:", e)
    traceback.print_exc()

finally:
    cap.release()
    pygame.mixer.quit()
    cv2.destroyAllWindows()
