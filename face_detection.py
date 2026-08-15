import cv2
import json
import time
import os
import numpy as np

# Simple face recognition
def recognize_face(face_img, known_faces):
    min_dist = float('inf')
    person_id = -1
    
    for id, reference_img in known_faces.items():
        # Simple comparison - in production use proper face recognition
        dist = np.linalg.norm(face_img - reference_img)
        if dist < min_dist:
            min_dist = dist
            person_id = id
    
    # If distance is too large, it's unknown
    if min_dist > 100:
        return -1
    return person_id

def calculate_proximity(face_width, frame_width):
    # Approximate distance based on face size
    # Closer face = larger width = higher proximity
    proximity = min(face_width / frame_width * 2, 1.0)
    return proximity

# Load known faces
known_faces = {}
if os.path.exists("faces/William/73.jpg"):
    known_faces[73] = cv2.imread("faces/William/73.jpg", cv2.IMREAD_GRAYSCALE)

# Your existing detection code
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) > 0:
        print(f"[FACE DETECTION] Face(s) detected! Count: {len(faces)}")
        x, y, w, h = faces[0]  # Use first face
        face_img = gray[y:y+h, x:x+w]
        proximity = calculate_proximity(w, frame.shape[1])
        
        # Try to recognize
        person_id = recognize_face(face_img, known_faces)
        is_authorized = (person_id == 73)
        person_name = "William" if is_authorized else "Unknown"
    else:
        print("[FACE DETECTION] No faces detected")
        proximity = 0.0
        person_id = -1
        is_authorized = False
        person_name = "None"
    
    # Send data to C#
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