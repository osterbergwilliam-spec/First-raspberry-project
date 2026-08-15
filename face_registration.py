#!/usr/bin/env python3
import subprocess
import time
import threading
import signal
import sys
import os
import cv2
import numpy as np
import socket
import base64
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Global variables
shutdown_flag = False
current_frame = None
detection_result = {"status": "No face detected", "authorized": False}
last_authorized = False
last_detection_time = 0
authorized_cooldown = 0

# Load your reference face
reference_face_path = "faces/your_face.jpg"
reference_face = None

if os.path.exists(reference_face_path):
    reference_face = cv2.imread(reference_face_path, cv2.IMREAD_GRAYSCALE)
    print("Reference face loaded for OpenCV recognition")

def is_you(face_img):
    if reference_face is None:
        return False
    
    try:
        face_img = cv2.resize(face_img, (reference_face.shape[1], reference_face.shape[0]))
        diff = cv2.absdiff(reference_face, face_img)
        diff_mean = float(np.mean(diff))
        print(f"Face match score: {diff_mean} (lower is better)")
        return diff_mean < 50
    except Exception as e:
        print(f"Error in face comparison: {e}")
        return False

# Web server for camera streaming
class StreamHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        global current_frame, detection_result
        
        if self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
            self.end_headers()
            
            while not shutdown_flag:
                if current_frame is not None:
                    try:
                        _, buffer = cv2.imencode('.jpg', current_frame)
                        self.wfile.write(bytes('--jpgboundary\r\nContent-Type: image/jpeg\r\n\r\n', 'utf-8'))
                        self.wfile.write(buffer.tobytes())
                        self.wfile.write(b'\r\n')
                    except Exception as e:
                        print(f"Error encoding frame: {e}")
                        break
                time.sleep(0.033)  # ~30fps
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
<!DOCTYPE html>
<html>
<head>
    <title>Camera Stream</title>
</head>
<body>
    <h1>Camera Stream</h1>
    <img src="/stream.mjpg" alt="Camera feed">
</body>
</html>
            ''')

# Start web server
def start_web_server():
    try:
        server = HTTPServer(('0.0.0.0', 8080), StreamHandler)
        print("Web server started on port 8080")
        server.serve_forever()
    except Exception as e:
        print(f"Error starting web server: {e}")

# Face detection and streaming
def detection_and_streaming():
    global current_frame, detection_result, shutdown_flag
    global last_authorized, last_detection_time, authorized_cooldown
    
    # Try different camera backends
    backends = [cv2.CAP_V4L2, cv2.CAP_GSTREAMER, cv2.CAP_FFMPEG]
    cap = None
    
    for backend in backends:
        try:
            cap = cv2.VideoCapture(0, backend)
            if cap.isOpened():
                print(f"Camera opened with backend {backend}")
                break
        except:
            continue
    
    if not cap or not cap.isOpened():
        print("Failed to open camera with any backend")
        return
    
    # Set camera parameters for better performance
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
    
    face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    
    # Face recognition timing
    last_recognition_time = 0
    recognition_interval = 0.5  # Recognize every 0.5 seconds
    
    while not shutdown_flag:
        current_time = time.time()
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue
        
        # Store current frame for streaming
        current_frame = frame.copy()
        
        # Face detection (every frame)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0 and reference_face is not None:
            x, y, w, h = faces[0]
            
            # Calculate proximity
            face_width = w
            frame_width = frame.shape[1]
            proximity = min(face_width / frame_width * 2, 1.0)
            
            if proximity >= 0.8:
                # Only do face recognition every 0.5 seconds
                if current_time - last_recognition_time > recognition_interval:
                    face_img = gray[y:y+h, x:x+w]
                    is_authorized = is_you(face_img)
                    
                    person_name = "William" if is_authorized else "Unknown"
                    print(f"Face detected: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}")
                    
                    # Draw rectangle
                    cv2.rectangle(frame, (x, y), (x+w, y+h), 
                                 (0, 255, 0) if is_authorized else (0, 0, 255), 2)
                    
                    # Only send to C# if authorization status changed
                    if is_authorized != last_authorized:
                        try:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.connect(('localhost', 9999))
                                message = f"{proximity},{73 if is_authorized else -1},{len(faces)},{person_name},{is_authorized}"
                                s.sendall(message.encode())
                                print(f"Sent to C#: Authorized={is_authorized}")
                        except Exception as e:
                            print(f"Socket error: {e}")
                    
                    last_authorized = is_authorized
                    last_recognition_time = current_time
                else:
                    # Use last known authorization status
                    cv2.rectangle(frame, (x, y), (x+w, y+h), 
                                 (0, 255, 0) if last_authorized else (0, 0, 255), 2)
            else:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
                # Reset authorization if face is too far
                if last_authorized:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect(('localhost', 9999))
                            message = f"{proximity},-1,{len(faces)},Too far for recognition,False"
                            s.sendall(message.encode())
                            print("Sent to C#: Too far for recognition")
                    except:
                        pass
                    last_authorized = False
        else:
            # No face detected
            if last_authorized:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect(('localhost', 9999))
                        message = f"0.0,-1,0,None,False"
                        s.sendall(message.encode())
                        print("Sent to C#: No face detected")
                except:
                    pass
                last_authorized = False
        
        time.sleep(0.01)  # Very small delay for high responsiveness
    
    cap.release()

# Start C# smart lock system
def start_lock_system():
    global shutdown_flag
    process = subprocess.Popen(["dotnet", "run"])
    
    while not shutdown_flag:
        time.sleep(1)
        if process.poll() is not None:
            print("Lock system process ended")
            break
    
    process.terminate()

# Main
if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda s, f: setattr(sys.modules[__name__], 'shutdown_flag', True))
    
    print("Starting smart lock system with camera streaming...")
    
    # Start web server
    web_thread = threading.Thread(target=start_web_server)
    web_thread.daemon = True
    web_thread.start()
    
    # Start face detection and streaming
    detection_thread = threading.Thread(target=detection_and_streaming)
    detection_thread.daemon = True
    detection_thread.start()
    
    # Wait a moment
    time.sleep(2)
    
    # Start lock system
    lock_thread = threading.Thread(target=start_lock_system)
    lock_thread.daemon = True
    lock_thread.start()
    
    print("All systems started!")
    print("Face detection: Running")
    print("Smart lock system: Running")
    print("Camera streaming: Running")
    print("In OBS: Add Media Source → http://YOUR_PI_IP:8080/stream.mjpg")
    
    # Keep main thread alive
    try:
        while not shutdown_flag:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        shutdown_flag = True