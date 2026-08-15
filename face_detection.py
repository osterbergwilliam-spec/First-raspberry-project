import cv2
import json
import time
import os
import numpy as np
import socket
import face_recognition

# Socket connection to C#
def send_to_csharp(data):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 9999))
            s.sendall(json.dumps(data).encode())
            print("[SOCKET] Data sent to C# app")
    except Exception as e:
        print(f"[SOCKET] Connection failed, falling back to JSON: {e}")
        # Fallback to JSON file
        try:
            with open('input.json', 'w') as f:
                json.dump(data, f)
        except Exception as e2:
            print(f"[ERROR] Failed to write JSON: {e2}")

# Load your reference face
reference_face_path = "faces/your_face.jpg"
known_image = None
known_encoding = None

if os.path.exists(reference_face_path):
    known_image = face_recognition.load_image_file(reference_face_path)
    known_encoding = face_recognition.face_encodings(known_image)[0]
    print("Reference face loaded for AI recognition")
else:
    print("Warning: Reference face not found at", reference_face_path)

# Initialize camera
cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        print("Failed to capture frame")
        time.sleep(1)
        continue
    
    # Convert for face_recognition library
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find faces
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    if face_locations:
        print(f"[AI DETECTION] Face(s) detected! Count: {len(face_locations)}")
    
    if face_locations and known_encoding is not None:
        # Get first face
        top, right, bottom, left = face_locations[0]
        
        # Calculate proximity based on face size
        face_width = right - left
        frame_width = frame.shape[1]
        proximity = min(face_width / frame_width * 2, 1.0)
        
        print(f"Face width: {face_width}px, Proximity: {proximity:.2f}")
        
        if proximity >= 0.8:  # Close enough for recognition
            # Compare faces using AI
            matches = face_recognition.compare_faces([known_encoding], face_encodings[0])
            is_authorized = matches[0]
            
            print(f"AI recognition: {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}")
            
            person_name = "William" if is_authorized else "Unknown"
            person_id = 73 if is_authorized else -1
        else:
            is_authorized = False
            person_name = "Too far for recognition"
            person_id = -1
    else:
        proximity = 0.0
        is_authorized = False
        person_name = "None" if not face_locations else "Unknown"
        person_id = -1
    
    # Create data for C# app
    data = {
        "Proximity": proximity,
        "Value": person_id,
        "FaceCount": len(face_locations),
        "PersonName": person_name,
        "IsAuthorized": is_authorized
    }
    
    # Send via socket
    send_to_csharp(data)
    
    time.sleep(1)