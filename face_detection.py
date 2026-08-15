#!/usr/bin/env python3
import json
import cv2
import time
import os
import socket
import numpy as np
import signal
import sys

# Add signal handling
def signal_handler(sig, frame):
    print("\nStopping face detection...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

# Load your reference face
reference_face_path = "faces/your_face.jpg"
reference_face = None

if os.path.exists(reference_face_path):
    reference_face = cv2.imread(reference_face_path, cv2.IMREAD_GRAYSCALE)
    print("Reference face loaded for OpenCV recognition")

def is_you(face_img):
    if reference_face is None:
        return False
    
    face_img = cv2.resize(face_img, (reference_face.shape[1], reference_face.shape[0]))
    diff = cv2.absdiff(reference_face, face_img)
    diff_mean = np.mean(diff)
    
    return diff_mean < 50

# Try a few common Raspberry Pi/USB camera device paths.
# If no camera is connected yet, keep retrying instead of exiting immediately.
camera_devices = ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video10"]
cap = None

while cap is None or not cap.isOpened():
    for device in camera_devices:
        candidate = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if candidate.isOpened():
            cap = candidate
            print(f"Camera opened with device: {device}")
            break

        candidate.release()
        print(f"Could not open camera device: {device}")

    if cap is None or not cap.isOpened():
        print("No camera detected. Please check permissions and camera connection. Retrying in 5 seconds...")
        time.sleep(5)

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Function to send data directly to C# via socket
def send_to_csharp(proximity, is_authorized, person_name, face_count):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 9999))
            message = {
                "Proximity": proximity,
                "Value": 73 if is_authorized else -1,
                "FaceCount": face_count,
                "PersonName": person_name,
                "IsAuthorized": is_authorized,
            }
            s.sendall(json.dumps(message).encode())
        return True
    except Exception as e:
        print(f"Socket error: {e}")
        return False

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to read from camera")
            time.sleep(0.1)
            continue
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0 and reference_face is not None:
            x, y, w, h = faces[0]
            
            # Calculate proximity based on face size
            face_width = w
            frame_width = frame.shape[1]
            proximity = min(face_width / frame_width * 2, 1.0)
            
            if proximity >= 0.8:
                face_img = gray[y:y+h, x:x+w]
                is_authorized = is_you(face_img)
                
                person_name = "William" if is_authorized else "Unknown"
                print(f"Face detected: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}")
                
                send_to_csharp(proximity, is_authorized, person_name, len(faces))
            else:
                is_authorized = False
                person_name = "Too far for recognition"
                print(f"Face detected but too far (proximity: {proximity:.2f})")
                
                send_to_csharp(proximity, is_authorized, person_name, len(faces))
        else:
            is_authorized = False
            person_name = "None" if len(faces) == 0 else "Unknown"
            send_to_csharp(0.0, is_authorized, person_name, len(faces))
        
        time.sleep(0.5)
except KeyboardInterrupt:
    print("\nStopping face detection...")
finally:
    cap.release()
