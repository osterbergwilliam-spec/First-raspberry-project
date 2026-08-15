import subprocess
import time
import threading

# Start face detection in background
def start_detection():
    subprocess.run(["python3", "face_detection.py"])

# Start C# smart lock system
def start_lock_system():
    subprocess.run(["dotnet", "run"])

# Run both in parallel
if __name__ == "__main__":
    print("Starting smart lock system...")
    
    # Start face detection
    detection_thread = threading.Thread(target=start_detection)
    detection_thread.daemon = True
    detection_thread.start()
    
    # Wait a moment for detection to initialize
    time.sleep(2)
    
    # Start lock system
    start_lock_system()
