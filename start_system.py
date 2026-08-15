#!/usr/bin/env python3
import subprocess
import time
import threading
import signal
import sys
import os
import cv2
import numpy as np
import json
import socket
import base64
from http.server import HTTPServer, SimpleHTTPRequestHandler

shutdown_flag = False
current_frame = None
detection_result = {"status": "No face detected", "authorized": False}

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
        return diff_mean < 50
    except Exception as e:
        print(f"Error in face comparison: {e}")
        return False


def handle_shutdown(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    print("\nShutting down gracefully...")
    raise SystemExit(0)


class StreamHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        global current_frame, detection_result

        if self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Content-type", "multipart/x-mixed-replace; boundary=--jpgboundary")
            self.end_headers()

            while not shutdown_flag:
                if current_frame is not None:
                    _, buffer = cv2.imencode(".jpg", current_frame)
                    self.wfile.write(b"--jpgboundary\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                    self.wfile.write(buffer.tobytes())
                    self.wfile.write(b"\r\n")
                time.sleep(0.1)
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b'''
<!DOCTYPE html>
<html>
<head><title>Camera Stream</title></head>
<body>
    <h1>Camera Stream</h1>
    <img src="/stream.mjpg" alt="Camera feed" />
</body>
</html>
''')


def start_web_server():
    server = HTTPServer(("0.0.0.0", 8080), StreamHandler)
    print("Web camera stream available at http://192.168.1.40:8080/stream.mjpg")
    server.serve_forever()


def send_to_csharp(proximity, is_authorized, person_name, face_count):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(("127.0.0.1", 9999))
            payload = {
                "Proximity": proximity,
                "Value": 73 if is_authorized else -1,
                "FaceCount": face_count,
                "PersonName": person_name,
                "IsAuthorized": is_authorized,
            }
            s.sendall(json.dumps(payload).encode())
        return True
    except Exception:
        return False


def detection_and_streaming():
    global current_frame, detection_result, shutdown_flag

    camera_devices = ["/dev/video0", "/dev/video1", "/dev/video2", "/dev/video10"]
    cap = None

    for device in camera_devices:
        candidate = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if candidate.isOpened():
            cap = candidate
            print(f"Camera opened with device: {device}")
            break
        candidate.release()

    if cap is None or not cap.isOpened():
        print("No camera detected. Please check permissions and camera connection.")
        return

    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

    while not shutdown_flag:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.2)
            continue

        current_frame = frame.copy()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) > 0 and reference_face is not None:
            x, y, w, h = faces[0]
            face_size = max(w, h)
            frame_size = max(frame.shape[0], frame.shape[1])
            proximity = min((face_size / frame_size) * 3.0, 1.0)

            if proximity >= 0.8:
                face_img = gray[y:y + h, x:x + w]
                is_authorized = is_you(face_img)
                person_name = "William" if is_authorized else "Unknown"
                detection_result = {
                    "status": f"Face detected: {person_name} - {'AUTHORIZED' if is_authorized else 'UNAUTHORIZED'}",
                    "authorized": is_authorized,
                }

                cv2.rectangle(frame, (x, y), (x + w, y + h),
                              (0, 255, 0) if is_authorized else (0, 0, 255), 2)
                send_to_csharp(proximity, is_authorized, person_name, len(faces))
            else:
                is_authorized = False
                person_name = "Too far for recognition"
                detection_result = {
                    "status": f"Face detected but too far for recognition (proximity: {proximity:.2f})",
                    "authorized": False,
                }
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
                send_to_csharp(proximity, is_authorized, person_name, len(faces))
        else:
            detection_result = {"status": "No face detected", "authorized": False}
            send_to_csharp(0.0, False, "None", len(faces))

        current_frame = frame.copy()
        time.sleep(0.5)

    cap.release()


def start_lock_system():
    global shutdown_flag
    process = subprocess.Popen(["dotnet", "run"])

    while not shutdown_flag:
        time.sleep(1)
        if process.poll() is not None:
            print("Lock system process ended")
            break

    if process.poll() is None:
        process.terminate()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)

    print("Starting smart lock system with camera streaming...")

    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    detection_thread = threading.Thread(target=detection_and_streaming, daemon=True)
    detection_thread.start()

    time.sleep(2)

    lock_thread = threading.Thread(target=start_lock_system, daemon=True)
    lock_thread.start()

    print("All systems started!")
    print("Face detection: Running")
    print("Smart lock system: Running")
    print("Camera streaming: Running")
    print("In OBS: Add Media Source -> URL -> http://192.168.1.40:8080/stream.mjpg")

    try:
        while not shutdown_flag:
            time.sleep(1)
    except KeyboardInterrupt:
        shutdown_flag = True
        print("\nShutting down...")
