# Intruder Detection and Smart Alert System for Visually Impaired Person
## Description
This project is an AI and IoT-based security system designed to assist visually impaired individuals. It detects intruders, suspicious behaviors, and environmental threats, providing real-time voice and haptic alerts to the user. Simultaneously, it notifies caregivers or family members via Firebase and automated emergency calls using Twilio or Google Dialer API. The system ensures adaptive silent SOS alerts, smart home integration, and multi-device accessibility, enhancing the safety, autonomy, and confidence of visually impaired users.
## Features
- AI-powered intruder detection using **YOLOv8**
- Human pose estimation for behavior analysis (hands-up, crouching, lying)
- Sound recognition with **Whisper AI** for environmental awareness
- Adaptive silent SOS mode for covert alerts
- Real-time voice and haptic feedback for visually impaired users
- IoT smart home integration: smart locks and lights
- Multi-device support: Android app, wearable devices, and cloud notifications
- Cloud-based alert notifications through **Firebase**

## Technology Stack
- **Backend:** Python, Firebase, Twilio API
- **Frontend:** Android Studio (Java/Kotlin)
- **AI/ML Models:** YOLOv8, MediaPipe, Whisper AI
- **IoT Devices:** PIR sensors, cameras, smart locks, smart lights
- **Cloud Services:** Firebase Cloud Messaging, Firestore Database## Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/visually_imp_person.git

2.**Navigate to the project folder:** 'cd visually_imp_person'

3.**Install Python dependencies:** 'pip install -r requirements.txt'

4.**Set up Firebase**

    1.Add your Firebase project credentials in config/firebase_config.json
    2.Enable Firebase Cloud Messaging
    3.Configure Twilio / Google Dialer API
    4.Add API keys in config/alerts_config.json
    5.Run the detection module
    6.python detect_intruder.py

**Usage**
   1.Launch the AI detection script to monitor intruders.
   2.Receive voice or haptic alerts on your mobile device.
   3.Notifications sent to caregivers via Firebase and automated emergency calls.
   4.Integrate smart home devices to automatically lock doors or turn on lights.
