import subprocess
import time
import threading
import signal
import sys

# Global flag for shutdown
shutdown_flag = False

def handle_shutdown(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    print("\nShutting down gracefully...")
    sys.exit(0)

# Start face detection in background
def start_detection():
    global shutdown_flag
    process = subprocess.Popen(["python3", "face_detection.py"])
    
    while not shutdown_flag:
        time.sleep(1)
        if process.poll() is not None:
            print("Face detection process ended")
            break
    
    process.terminate()

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

# Run both in parallel
if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)
    
    print("Starting smart lock system...")
    
    # Start face detection
    detection_thread = threading.Thread(target=start_detection)
    detection_thread.daemon = True
    detection_thread.start()
    
    # Wait a moment for detection to initialize
    time.sleep(2)
    
    # Start lock system
    start_lock_system()