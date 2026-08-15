import cv2
import json
import time
import os
import socket
import numpy as np

# Load your reference face
reference_face_path = "faces/your_face.jpg"
reference_face = None

if os.path.exists(reference_face_path):
    reference_face = cv2.imread(reference_face_path, cv2.IMREAD_GRAYSCALE)
    print("Reference face loaded for OpenCV recognition")

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

# Initialize camera
cap = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

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
        return True
    except:
        return False

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(1)
        continue
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    if len(faces) > 0 and reference_face is not None:
        # Get first face
        x, y, w, h = faces[0]

        # Use a more stable size estimate based on the largest detected face dimension.
        # This keeps the value in a 0.0-1.0 range and makes recognition trigger more
        # consistently as the user moves closer to the camera.
        face_size = max(w, h)
        frame_size = max(frame.shape[0], frame.shape[1])
        proximity = min((face_size / frame_size) * 3.0, 1.0)

        print(f"Face detected! Size: {face_size}px, Proximity: {proximity:.2f}")

        if proximity >= 0.8:
            face_img = gray[y:y+h, x:x+w]
            is_authorized = is_you(face_img)

            person_name = "William" if is_authorized else "Unknown"
            print(f"OpenCV recognition: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}")
        else:
            is_authorized = False
            person_name = "Too far for recognition"
    else:
        proximity = 0.0
        is_authorized = False
        person_name = "None" if len(faces) == 0 else "Unknown"

    # Send directly to C# via socket
    send_to_csharp(proximity, is_authorized, person_name, len(faces))
    
    time.sleep(1)