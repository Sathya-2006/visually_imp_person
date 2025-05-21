import cv2
import time
import pyttsx3
import firebase_admin
from firebase_admin import credentials, firestore
from ultralytics import YOLO
import mediapipe as mp
from twilio.rest import Client

# Initialize Firebase
cred = credentials.Certificate("serviceaccountKey.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Twilio credentials
TWILIO_SID = "------"
TWILIO_AUTH_TOKEN = "------"
TWILIO_PHONE = "+12165161305"
USER_PHONE = "+917603800698"

twilio_client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

# YOLOv8 for object detection
model = YOLO("yolov8n.pt")

# MediaPipe Pose
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

# Text-to-Speech
engine = pyttsx3.init()

# Camera and detection zone
cap = cv2.VideoCapture(0)
DOOR_ZONE = (200, 100, 400, 400)

SUSPICIOUS_TIME_THRESHOLD = 5
person_last_seen_time = None
person_in_zone = False

# Alerting Function
def send_alert(msg):
    print("[ALERT]", msg)
    engine.say(msg)
    engine.runAndWait()

    # Store in Firebase
    db.collection("alerts").add({
        "timestamp": firestore.SERVER_TIMESTAMP,
        "alert": msg
    })

    # SMS
    twilio_client.messages.create(
        body=msg,
        from_=TWILIO_PHONE,
        to=USER_PHONE
    )

    # Call
    call = twilio_client.calls.create(
        twiml='<Response><Say>' + msg + '</Say></Response>',
        from_=TWILIO_PHONE,
        to=USER_PHONE
    )

print("🎯 Intruder Detection Started")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    results = model(frame)

    motion = False
    suspicious = False
    weapon_detected = False
    mask_detected = False

    for r in results:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            label = model.names[cls_id]
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            if label == "person" and conf > 0.5:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                dx1, dy1, dx2, dy2 = DOOR_ZONE
                if dx1 < center_x < dx2 and dy1 < center_y < dy2:
                    person_in_zone = True
                    if person_last_seen_time is None:
                        person_last_seen_time = time.time()

                    # Check if no motion
                    if time.time() - person_last_seen_time > SUSPICIOUS_TIME_THRESHOLD:
                        suspicious = True
                        send_alert("Suspicious loitering detected near door.")

                    # Pose Estimation
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pose_results = pose.process(frame_rgb)
                    if pose_results.pose_landmarks:
                        left_hip = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_HIP]
                        left_knee = pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.LEFT_KNEE]
                        if left_knee.y < left_hip.y:
                            send_alert("Suspicious crouching pose detected.")
                else:
                    person_in_zone = False
                    person_last_seen_time = None

            # Weapon or Mask detection
            if label in ["knife", "gun"] and conf > 0.4:
                weapon_detected = True
                send_alert(f"Weapon detected: {label}")

            if label == "mask" and conf > 0.5:
                mask_detected = True
                send_alert("Person wearing a mask detected.")

    # Draw door zone
    cv2.rectangle(frame, (DOOR_ZONE[0], DOOR_ZONE[1]), (DOOR_ZONE[2], DOOR_ZONE[3]), (0, 0, 255), 2)
    cv2.imshow("Intruder Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
