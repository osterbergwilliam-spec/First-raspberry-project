import cv2
import face_recognition
import json
import time
import os
import base64
import threading
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import parse_qs

# Global variables for sharing data between threads
current_frame = None
detection_result = {"status": "No face detected", "authorized": False}

class ViewerHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        global current_frame, detection_result
        
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(detection_result).encode())
        elif self.path == '/frame':
            if current_frame is not None:
                # Encode frame as JPEG
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
        
        // Update every second
        setInterval(() => {
            updateStatus();
            updateFrame();
        }, 1000);
        
        // Initial update
        updateStatus();
        updateFrame();
    </script>
</body>
</html>
            ''')

# Start the web server in a thread
def start_server():
    server = HTTPServer(('localhost', 8080), ViewerHandler)
    server.serve_forever()

# Start server thread
server_thread = threading.Thread(target=start_server)
server_thread.daemon = True
server_thread.start()
print("[SERVER] Web viewer started on http://localhost:8080")

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

# Main detection loop
print("[SYSTEM] Starting AI face detection with web viewer...")
while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(1)
        continue
    
    # Store current frame for web viewer
    current_frame = frame.copy()
    
    # Convert for face_recognition library
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Find faces
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
            detection_result = {
                "status": f"Face detected: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}",
                "authorized": is_authorized
            }
            
            # Draw rectangle on frame
            cv2.rectangle(frame, (left, top), (right, bottom), 
                         (0, 255, 0) if is_authorized else (0, 0, 255), 2)
            
            # Send to C# via socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', 9999))
                    data = {
                        "Proximity": proximity,
                        "Value": 73 if is_authorized else -1,
                        "FaceCount": len(face_locations),
                        "PersonName": person_name,
                        "IsAuthorized": is_authorized
                    }
                    s.sendall(json.dumps(data).encode())
                    print(f"[SOCKET] {person_name} - Authorized: {is_authorized}")
            except Exception as e:
                print(f"[WARNING] Could not connect to C# app: {e}")
        else:
            detection_result = {
                "status": f"Face detected but too far for recognition (proximity: {proximity:.2f})",
                "authorized": False
            }
            
            # Draw rectangle on frame
            cv2.rectangle(frame, (left, top), (right, bottom), (255, 255, 0), 2)
    else:
        detection_result = {
            "status": "No face detected",
            "authorized": False
        }
    
    time.sleep(1)
