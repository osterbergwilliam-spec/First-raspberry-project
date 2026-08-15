import cv2
import json
import time

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    # Send face data
    data = {
        "Proximity": min(len(faces) * 0.2, 1.0),
        "Value": 73 if faces else -1,
        "FaceCount": len(faces),
        "FaceData": [{"x": int(x), "y": int(y), "w": int(w), "h": int(h)} for (x, y, w, h) in faces]
    }
    
    with open('input.json', 'w') as f:
        json.dump(data, f)
    
    time.sleep(1)
