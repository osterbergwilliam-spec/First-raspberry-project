import cv2
import os
import urllib.request

# Download cascade file if it doesn't exist
if not os.path.exists("haarcascade_frontalface_default.xml"):
    print("Downloading cascade file...")
    urllib.request.urlretrieve(
        "https://github.com/opencv/opencv/raw/master/data/haarcascades/haarcascade_frontalface_default.xml",
        "haarcascade_frontalface_default.xml"
    )

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

# Create directory for faces
os.makedirs("faces", exist_ok=True)

print("Position your face in the camera and press 's' to capture")
print("This will create your reference image for recognition")

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    # Fix: Check if faces array is not empty
    face_detected = len(faces) > 0
    
    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
    
    cv2.imshow('Register Your Face', frame)
    
    # Fix: Use face_detected instead of faces
    if cv2.waitKey(1) & 0xFF == ord('s') and face_detected:
        x, y, w, h = faces[0]
        face_img = gray[y:y+h, x:x+w]
        cv2.imwrite("faces/your_face.jpg", face_img)
        print("Face saved! You can now close this window.")
        break

cv2.destroyAllWindows()