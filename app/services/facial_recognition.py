import cv2
import numpy as np
import face_recognition
from sqlalchemy import text
from app.core.database import SessionLocal


CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def load_known_faces():
    """Load face encodings and names from the employees table."""
    db = SessionLocal()
    names = []
    encodings = []
    try:
        rows = db.execute(
            text(
                "SELECT emp_id, COALESCE(emp_name, 'Employee ' || emp_id), emp_photo "
                "FROM employees WHERE emp_photo IS NOT NULL"
            )
        ).fetchall()
        for emp_id, emp_name, emp_photo in rows:
            if not emp_photo:
                continue
            np_img = np.frombuffer(emp_photo, dtype=np.uint8)
            img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)
            if img is None:
                continue
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            face_encs = face_recognition.face_encodings(rgb)
            if not face_encs:
                continue
            encodings.append(face_encs[0])
            names.append(emp_name or f"Employee {emp_id}")
    finally:
        db.close()
    return names, encodings


def save_employee_photo(emp_name: str, face_img):
    db = SessionLocal()
    try:
        ok, buffer = cv2.imencode(".jpg", face_img)
        if not ok:
            raise RuntimeError("Could not encode face image")
        db.execute(
            text("INSERT INTO employees (emp_name, emp_photo) VALUES (:name, :photo)"),
            {"name": emp_name, "photo": buffer.tobytes()},
        )
        db.commit()
    finally:
        db.close()


def capture_and_store_face(emp_name: str, num_samples: int = 5):
    """Capture face samples from the webcam and store the best crop in the DB."""
    face_detector = cv2.CascadeClassifier(CASCADE_PATH)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    captured_faces = []
    try:
        while len(captured_faces) < num_samples:
            ret, frame = cap.read()
            if not ret:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            for (x, y, w, h) in faces:
                face_crop = frame[y : y + h, x : x + w]
                captured_faces.append(face_crop)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"Captured {len(captured_faces)}/{num_samples}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
            cv2.imshow("Enroll Face", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        if not captured_faces:
            raise RuntimeError("No faces captured; ensure lighting and camera position are ok")
        sharpest = max(captured_faces, key=lambda img: cv2.Laplacian(img, cv2.CV_64F).var())
        save_employee_photo(emp_name, sharpest)
    finally:
        cap.release()
        cv2.destroyAllWindows()


def recognize_from_db(tolerance: float = 0.45):
    """Run realtime face recognition using faces stored in the DB."""
    known_names, known_encodings = load_known_faces()
    if not known_encodings:
        print("No stored photos in DB. Run capture_and_store_face() first.")
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            small = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

            locations = face_recognition.face_locations(rgb_small, model="hog")
            encs = face_recognition.face_encodings(rgb_small, locations)

            for (top, right, bottom, left), face_enc in zip(locations, encs):
                distances = face_recognition.face_distance(known_encodings, face_enc)
                best_idx = int(np.argmin(distances)) if len(distances) else -1
                name = "Unknown"
                if best_idx >= 0 and distances[best_idx] <= tolerance:
                    name = known_names[best_idx]

                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    name,
                    (left, top - 10 if top - 10 > 10 else top + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0) if name != "Unknown" else (0, 0, 255),
                    2,
                )

            cv2.imshow("Access Control - Face Recognition", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Capture and recognize faces using the access_control.db storage"
    )
    parser.add_argument(
        "--enroll",
        metavar="NAME",
        help="Capture a new face for the given employee name and store it in the DB",
    )
    parser.add_argument(
        "--recognize",
        action="store_true",
        help="Run realtime recognition using faces stored in the DB",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=5,
        help="Number of samples to capture when enrolling (default: 5)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.45,
        help="Matching tolerance; lower is stricter (default: 0.45)",
    )

    args = parser.parse_args()

    if args.enroll:
        capture_and_store_face(args.enroll, num_samples=args.samples)
    if args.recognize:
        recognize_from_db(tolerance=args.tolerance)
    if not args.enroll and not args.recognize:
        parser.print_help()
