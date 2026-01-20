"""app.services.facial_recognition

Face recognition for access control.

Two usage styles:
- CLI (run this file): enroll / recognize using OpenCV windows.
- Server/video streaming: call `recognize_and_annotate_frame(...)` on frames.

Important:
- LBPH recognizer is in `cv2.face` and requires `opencv-contrib-python`.
"""

from __future__ import annotations

import os
import sys

# Allow running this file directly: `py app/services/facial_recognition.py ...`
# by ensuring the project root (parent of `app/`) is on sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time

import cv2
import numpy as np
from sqlalchemy import text

from app.core.database import SessionLocal

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)


def _lbph_available() -> bool:
    return hasattr(cv2, "face") and hasattr(cv2.face, "LBPHFaceRecognizer_create")


def _create_lbph_recognizer():
    if not _lbph_available():
        raise RuntimeError(
            "OpenCV LBPH is not available (cv2.face missing). "
            "Install opencv-contrib-python and uninstall opencv-python/opencv-python-headless."
        )
    return cv2.face.LBPHFaceRecognizer_create()


def crop_and_normalize(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 3:
        gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray_img = image
   
    # Wykrywanie twarzy
    faces = FACE_CASCADE.detectMultiScale(gray_img, 1.1, 5, minSize=(60, 60))
    
    if len(faces) > 0:
        # Wybierz największą twarz (najbliższą kamery)
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face = gray_img[y : y + h, x : x + w]
    else:
        # Fallback: jeśli nie wykryto twarzy, spróbuj wyciąć środek (dla debugowania)
        # W produkcji lepiej rzucić błąd
        raise ValueError("Nie wykryto twarzy na zdjęciu")

    # Normalizacja (wyrównanie histogramu i rozmiaru)
    face = cv2.resize(face, (200, 200))
    return face



def load_faces_from_db():
    db = SessionLocal()
    faces: list[np.ndarray] = []
    names: list[str] = []
    try:
        # Pobieramy tylko te wiersze, które mają zdjęcie
        result = db.execute(text("SELECT emp_name, emp_photo FROM employees WHERE emp_photo IS NOT NULL"))
        for emp_name, emp_photo in result:
            if not emp_photo: continue
            
            # Dekodowanie BLOBa do obrazu
            img_array = np.frombuffer(emp_photo, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            
            if img is None: continue
            
            # Tutaj zakładamy, że w bazie są już "gotowe maski", 
            # ale dla pewności możemy przepuścić przez normalizację
            try:
                # Jeśli zdjęcie w bazie jest już 200x200, resize nic nie zepsuje
                face = cv2.resize(img, (200, 200)) 
                faces.append(face)
                names.append(emp_name or "Unknown")
            except Exception:
                pass
        return faces, names
    finally:
        db.close()


def train_lbph_from_db():
    known_faces, known_names = load_faces_from_db()
    if len(known_faces) == 0:
        raise RuntimeError("No faces in database. Add users with emp_photo first.")

    recognizer = _create_lbph_recognizer()
    labels = np.arange(len(known_names), dtype=np.int32)
    recognizer.train(known_faces, labels)
    return recognizer, known_names


def save_face_to_db(name: str, face_image: np.ndarray):
    """Save/update a face photo in the database for the given name."""
    db = SessionLocal()
    try:
        ok, buffer = cv2.imencode(".jpg", face_image)
        if not ok:
            raise RuntimeError("Could not encode face image")

        existing = db.execute(
            text("SELECT emp_id FROM employees WHERE emp_name = :name ORDER BY emp_id DESC LIMIT 1"),
            {"name": name},
        ).first()

        if existing:
            db.execute(
                text("UPDATE employees SET emp_photo = :photo WHERE emp_id = :id"),
                {"photo": buffer.tobytes(), "id": existing[0]},
            )
        else:
            db.execute(
                text("INSERT INTO employees (emp_name, emp_photo) VALUES (:name, :photo)"),
                {"name": name, "photo": buffer.tobytes()},
            )

        db.commit()
        print(f"✓ Saved face for: {name}")
    finally:
        db.close()


def enroll_face(name: str):
    """Capture a face from webcam and save to database."""
    print(f"Enrolling: {name}")
    print("Look at the camera. Press SPACE to capture, ESC to cancel.")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Cannot read from camera")
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))

            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    "Press SPACE to capture",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

            cv2.imshow("Enroll Face - SPACE to capture, ESC to cancel", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == 32:  # SPACE
                if len(faces) > 0:
                    x, y, w, h = faces[0]
                    face_img = gray[y : y + h, x : x + w]
                    face_img = crop_and_normalize(face_img)
                    save_face_to_db(name, face_img)
                    break
                print("No face detected. Try again.")
            elif key == 27:  # ESC
                print("Cancelled")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

def recognize_and_annotate_frame(frame_bgr, recognizer, known_names, threshold=90.0, now=None):
    if now is None: now = time.time()
    
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))
    
    # Liczba wykrytych twarzy (używane w video.py do logowania prób)
    face_count = len(faces)
    
    best_name = "Unknown"
    best_conf = 999.0

    for (x, y, w, h) in faces:
        try:
            # 1. Wycinamy twarz z klatki
            face_roi = gray[y:y+h, x:x+w]
            
            # 2. Przetwarzamy do formatu LBPH
            # Zamiast crop_and_normalize (który szuka twarzy w twarzy i powodował błąd),
            # robimy manualną normalizację, bo JUŻ mamy twarz (x,y,w,h)
            face_img = cv2.resize(face_roi, (200, 200))

            # 3. Predykcja
            label, confidence = recognizer.predict(face_img)
            
            if confidence < best_conf:
                best_conf = confidence
                if 0 <= label < len(known_names):
                    best_name = known_names[label]

            # Rysowanie
            color = (0, 255, 0) if confidence < threshold else (0, 0, 255)
            text_name = best_name if confidence < threshold else "Unknown"
            text = f"{text_name} ({confidence:.1f})"
            cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), color, 2)
            cv2.putText(frame_bgr, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
        except Exception as e:
            print(f"Błąd przetwarzania twarzy: {e}")
            continue
    final_name = best_name if best_conf < threshold else "Unknown"

    return final_name, best_conf, frame_bgr, face_count


def recognize_faces():
    """Start webcam and recognize faces from database (OpenCV window)."""
    print("Loading faces from database...")
    try:
        recognizer, known_names = train_lbph_from_db()
    except Exception as e:
        print(f"Error: {e}")
        return

    print(f"Loaded {len(known_names)} faces: {', '.join(known_names)}")
    print("Starting camera... Press Q to quit")

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Error: Cannot open camera")
        return

    threshold = 80.0
    last_name = "Unknown"
    last_conf = 999.0
    last_seen = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            name, conf, annotated, _face_count = recognize_and_annotate_frame(
                frame,
                recognizer=recognizer,
                known_names=known_names,
                threshold=threshold,
                last_state=(last_name, last_conf, last_seen),
                now=time.time(),
            )
            if name != "Unknown":
                last_name, last_conf, last_seen = name, conf, time.time()

            cv2.imshow("Access Control - Face Recognition", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Face Recognition for Access Control")
    parser.add_argument("--enroll", metavar="NAME", help="Enroll a new face with the given name")
    parser.add_argument("--recognize", action="store_true", help="Start face recognition from webcam")

    args = parser.parse_args()

    if args.enroll:
        enroll_face(args.enroll)
    elif args.recognize:
        recognize_faces()
    else:
        parser.print_help()
