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


def _crop_and_normalize(gray_img: np.ndarray) -> np.ndarray:
    faces = FACE_CASCADE.detectMultiScale(gray_img, 1.1, 5, minSize=(60, 60))
    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        face = gray_img[y : y + h, x : x + w]
    else:
        h, w = gray_img.shape
        m = min(h, w)
        y0 = (h - m) // 2
        x0 = (w - m) // 2
        face = gray_img[y0 : y0 + m, x0 : x0 + m]

    face = cv2.equalizeHist(face)
    face = cv2.resize(face, (200, 200))
    return face


def load_faces_from_db():
    """Load all face photos and names from database.

    Returns: (faces, names)
    - faces: list[np.ndarray] (200x200 grayscale)
    - names: list[str]
    """
    db = SessionLocal()
    faces: list[np.ndarray] = []
    names: list[str] = []

    try:
        result = db.execute(
            text("SELECT emp_name, emp_photo FROM employees WHERE emp_photo IS NOT NULL")
        )

        for emp_name, emp_photo in result:
            if not emp_photo:
                continue
            img_array = np.frombuffer(emp_photo, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            face = _crop_and_normalize(img)
            faces.append(face)
            names.append(emp_name or "Unknown")

        return faces, names
    finally:
        db.close()


def train_lbph_from_db():
    """Train an LBPH recognizer from employee photos stored in the DB.

    Returns: (recognizer, known_names)
    """
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
                    face_img = _crop_and_normalize(face_img)
                    save_face_to_db(name, face_img)
                    break
                print("No face detected. Try again.")
            elif key == 27:  # ESC
                print("Cancelled")
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


def recognize_and_annotate_frame(
    frame_bgr: np.ndarray,
    *,
    recognizer,
    known_names: list[str],
    threshold: float = 80.0,
    face_cascade=FACE_CASCADE,
    last_state=("Unknown", 999.0, 0.0),
    now: float | None = None,
):
    """Recognize faces on a single BGR frame and draw labels.

    Returns: (best_name, best_confidence, annotated_frame)
    - best_name: recognized employee name or "Unknown"
    - best_confidence: LBPH distance (lower is better)
    """
    if now is None:
        now = time.time()

    last_name, last_conf, last_seen = last_state

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))
    face_count = int(len(faces))

    best_name = "Unknown"
    best_conf = 999.0

    for (x, y, w, h) in faces:
        face_img = gray[y : y + h, x : x + w]
        face_img = _crop_and_normalize(face_img)

        label, confidence = recognizer.predict(face_img)
        confidence = float(confidence)

        if confidence < best_conf:
            best_conf = confidence
            if 0 <= int(label) < len(known_names):
                best_name = known_names[int(label)]
            else:
                best_name = "Unknown"

        # LBPH returns a distance (lower is better). Convert to a simple 0-100% score
        # relative to the recognition threshold so the UI isn't stuck at 0%.
        if threshold <= 0:
            conf_pct = 0.0
        else:
            conf_pct = max(0.0, min(100.0, (threshold - confidence) / threshold * 100.0))

        if confidence <= threshold:
            last_name = best_name
            last_conf = confidence
            last_seen = now

        if confidence <= threshold:
            name = last_name
            color = (0, 255, 0)
            text = f"{name} ({conf_pct:.0f}%) d={confidence:.1f}"
            decision = "IN DATABASE"
        elif last_name != "Unknown" and (now - last_seen) < 2.0:
            name = last_name
            color = (0, 200, 0)
            if threshold <= 0:
                last_pct = 0.0
            else:
                last_pct = max(0.0, min(100.0, (threshold - last_conf) / threshold * 100.0))
            text = f"{name} ({last_pct:.0f}%) d={last_conf:.1f}"
            decision = "IN DATABASE"
        else:
            name = "Unknown"
            color = (0, 0, 255)
            text = f"Unknown ({conf_pct:.0f}%) d={confidence:.1f}"
            decision = "NOT IN DATABASE"

        cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), color, 2)
        cv2.putText(frame_bgr, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.putText(frame_bgr, decision, (x, y + h + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    return best_name, best_conf, frame_bgr, face_count


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
