import cv2
import os

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
cap = cv2.VideoCapture(0)

def register_face(name, person_id):
    os.makedirs(f"faces/{name}", exist_ok=True)
    print(f"Register {name} (ID: {person_id}). Press 's' to capture.")
    
    while True:
        ret, frame = cap.read()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
        
        cv2.imshow('Register Face', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('s') and faces:
            x, y, w, h = faces[0]
            face_img = gray[y:y+h, x:x+w]
            cv2.imwrite(f"faces/{name}/{person_id}.jpg", face_img)
            print(f"Saved: faces/{name}/{person_id}.jpg")
            break
    
    cv2.destroyAllWindows()

# Register authorized user
register_face("William", 73)
