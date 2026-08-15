import cv2
import face_recognition
import socket
import json
import time
import os

# Load your reference face
reference_face_path = "faces/your_face.jpg"
known_image = None
known_encoding = None

if os.path.exists(reference_face_path):
    known_image = face_recognition.load_image_file(reference_face_path)
    known_encoding = face_recognition.face_encodings(known_image)[0]
    print("[AI] Reference face loaded for AI recognition")
else:
    print("[WARNING] Reference face not found at", reference_face_path)

# Initialize camera
cap = cv2.VideoCapture(0)

# Function to send data directly to C# via socket
def send_to_csharp(proximity, is_authorized, person_name, face_count):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', 9999))
            data = {
                "Proximity": proximity,
                "Value": 73 if is_authorized else -1,
                "FaceCount": face_count,
                "PersonName": person_name,
                "IsAuthorized": is_authorized
            }
            s.sendall(json.dumps(data).encode())
            print(f"[SOCKET] Data sent: {person_name} - Authorized: {is_authorized}")
            return True
    except Exception as e:
        print(f"[ERROR] Socket connection failed: {e}")
        return False

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Failed to capture frame")
        time.sleep(1)
        continue
    
    # Convert for face_recognition library
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find faces using AI
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
    
    if face_locations and known_encoding is not None:
        # Get first face
        top, right, bottom, left = face_locations[0]
        
        # Calculate proximity based on face size
        face_width = right - left
        frame_width = frame.shape[1]
        proximity = min(face_width / frame_width * 2, 1.0)
        
        if proximity >= 0.8:  # Close enough for recognition
            # Compare faces using AI
            matches = face_recognition.compare_faces([known_encoding], face_encodings[0])
            is_authorized = matches[0]
            
            person_name = "William" if is_authorized else "Unknown"
            print(f"[AI] Face recognized: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}")
        else:
            is_authorized = False
            person_name = "Too far for recognition"
            print(f"[AI] Face too far away - Proximity: {proximity:.2f}")
    else:
        proximity = 0.0
        is_authorized = False
        person_name = "None" if not face_locations else "Unknown"
        print(f"[AI] No faces detected")
    
    # Send directly to C# via socket
    send_to_csharp(proximity, is_authorized, person_name, len(face_locations))
    
    time.sleep(1)