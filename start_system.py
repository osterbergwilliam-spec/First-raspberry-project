import subprocess
import time
import threading
import signal
import sys
import socket

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


def wait_for_lock_socket(host="127.0.0.1", port=9999, timeout=30):
    deadline = time.time() + timeout

    while time.time() < deadline and not shutdown_flag:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)

    return False


if __name__ == "__main__":
    signal.signal(signal.SIGINT, handle_shutdown)

    print("Starting smart lock system...")

    lock_thread = threading.Thread(target=start_lock_system)
    lock_thread.daemon = True
    lock_thread.start()

    print("Waiting for C# lock socket on port 9999...")
    if not wait_for_lock_socket():
        print("C# lock socket did not start on port 9999.")
        shutdown_flag = True
        sys.exit(1)

    detection_thread = threading.Thread(target=start_detection)
    detection_thread.daemon = True
    detection_thread.start()

    while not shutdown_flag and lock_thread.is_alive() and detection_thread.is_alive():
        time.sleep(1)
