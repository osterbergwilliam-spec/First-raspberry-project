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


def start_detection():
    global shutdown_flag
    process = subprocess.Popen(["python3", "face_detection.py"])

    while not shutdown_flag:
        time.sleep(1)
        if process.poll() is not None:
            print("Face detection process ended")
            break

    if process.poll() is None:
        process.terminate()


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

    print("Starting smart lock system...")

    detection_thread = threading.Thread(target=start_detection)
    detection_thread.daemon = True
    detection_thread.start()

    time.sleep(2)

    start_lock_system()