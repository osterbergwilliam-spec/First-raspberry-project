import cv2
import json
import time

# Load face detection model
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Initialize camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    # Create data for your C# app
    data = {
        "Proximity": len(faces) * 0.2,  # Simple proximity calculation
        "Value": 73 if faces else -1     # 73 = authorized person
    }
    
    # Write to JSON file
    with open('input.json', 'w') as f:
        json.dump(data, f)
    
    time.sleep(1)  # Update every second
