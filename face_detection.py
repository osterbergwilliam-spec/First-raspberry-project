import cv2
import json
import time
import os
import numpy as np

# Load your reference face
reference_face = None
if os.path.exists("faces/your_face.jpg"):
    reference_face = cv2.imread("faces/your_face.jpg", cv2.IMREAD_GRAYSCALE)
    print("Reference face loaded")

def is_you(face_img):
    if reference_face is None:
        return False
    
    # Resize to match reference
    face_img = cv2.resize(face_img, (reference_face.shape[1], reference_face.shape[0]))
    
    # Simple comparison
    diff = cv2.absdiff(reference_face, face_img)
    diff_mean = np.mean(diff)
    
    print(f"Face match score: {diff_mean} (lower is better)")
    return diff_mean < 50

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) > 0:
        x, y, w, h = faces[0]
        
        # Calculate distance based on face width
        face_width = w
        frame_width = frame.shape[1]
        proximity = min(face_width / frame_width * 2, 1.0)
        
        print(f"Face detected! Proximity: {proximity:.2f} (width: {face_width}px)")
        
        if proximity < 0.3:
            print("Too far away for recognition")
        
        if proximity >= 0.8 and reference_face is not None:
            face_img = gray[y:y+h, x:x+w]
            is_authorized = is_you(face_img)
            person_name = "William" if is_authorized else "Unknown"
            person_id = 73 if is_authorized else -1
        else:
            is_authorized = False
            person_name = "Unknown" if proximity >= 0.3 else "Too far"
            person_id = -1
    else:
        proximity = 0.0
        is_authorized = False
        person_name = "None"
        person_id = -1
    
    data = {
        "Proximity": proximity,
        "Value": person_id,
        "FaceCount": len(faces),
        "PersonName": person_name,
        "IsAuthorized": is_authorized
    }
    
    with open('input.json', 'w') as f:
        json.dump(data, f)
    
    time.sleep(1)