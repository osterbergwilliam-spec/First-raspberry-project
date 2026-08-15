import json
import cv2
import time
import os
import socket
import numpy as np
import base64
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

# Global variables for sharing data between threads
current_frame = None
detection_result = {"status": "No face detected", "authorized": False}
csharp_connection_available = True

class ViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        global current_frame, detection_result
        
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # Convert bool to regular Python bool for JSON
            clean_result = {
                "status": detection_result["status"],
                "authorized": bool(detection_result["authorized"])
            }
            self.wfile.write(json.dumps(clean_result).encode())
        elif self.path == '/frame':
            if current_frame is not None:
                _, buffer = cv2.imencode('.jpg', current_frame)
                frame_bytes = base64.b64encode(buffer).decode()
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"image": frame_bytes}).encode())
        else:
            # Serve the HTML viewer
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'''
<!DOCTYPE html>
<html>
<head>
    <title>AI Face Detection Viewer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .authorized { background-color: #d4edda; color: #155724; }
        .unauthorized { background-color: #f8d7da; color: #721c24; }
        .no-face { background-color: #e2e3e5; color: #383d41; }
        img { max-width: 100%; border: 1px solid #ddd; }
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Face Detection Viewer</h1>
        <div id="status" class="status no-face">Loading...</div>
        <img id="frame" src="" alt="Camera feed">
    </div>
    
    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    statusDiv.textContent = data.status;
                    statusDiv.className = 'status ' + 
                        (data.authorized ? 'authorized' : 
                         data.status.includes('No face') ? 'no-face' : 'unauthorized');
                });
        }
        
        function updateFrame() {
            fetch('/frame')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('frame').src = 
                        'data:image/jpeg;base64,' + data.image;
                });
        }
        
        setInterval(() => {
            updateStatus();
            updateFrame();
        }, 1000);
        
        updateStatus();
        updateFrame();
    </script>
</body>
</html>
            ''')

# Start the web server in a thread
def start_server():
    server = HTTPServer(('0.0.0.0', 8080), ViewerHandler)
    server.serve_forever()

# Start server thread
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()

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

# Initialize camera
cap = cv2.VideoCapture(0)
face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

# Function to send data directly to C# via socket
def send_to_csharp(proximity, is_authorized, person_name, face_count):
    global csharp_connection_available

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('127.0.0.1', 9999))
            message = {
                "Proximity": proximity,
                "Value": 73 if is_authorized else -1,
                "FaceCount": face_count,
                "PersonName": person_name,
                "IsAuthorized": is_authorized
            }
            s.sendall(json.dumps(message).encode())
        if not csharp_connection_available:
            print("[SOCKET] Reconnected to C# app")
        csharp_connection_available = True
        return True
    except Exception as e:
        if csharp_connection_available:
            print(f"[WARNING] Could not connect to C# app: {e}")
        csharp_connection_available = False
        return False

while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(1)
        continue
    
    # Store current frame for web viewer
    current_frame = frame.copy()
    
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
            detection_result = {
                "status": f"Face detected: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}",
                "authorized": is_authorized
            }
            
            # Draw rectangle on frame
            cv2.rectangle(frame, (x, y), (x+w, y+h), 
                         (0, 255, 0) if is_authorized else (0, 0, 255), 2)
            
            send_to_csharp(proximity, is_authorized, person_name, len(faces))
        else:
            is_authorized = False
            person_name = "Too far for recognition"
            detection_result = {
                "status": f"Face detected but too far for recognition (proximity: {proximity:.2f})",
                "authorized": is_authorized
            }
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
            send_to_csharp(proximity, is_authorized, person_name, len(faces))
    else:
        is_authorized = False
        person_name = "None" if len(faces) == 0 else "Unknown"
        detection_result = {
            "status": "No face detected",
            "authorized": is_authorized
        }
        send_to_csharp(0.0, is_authorized, person_name, len(faces))
    
    time.sleep(1)
