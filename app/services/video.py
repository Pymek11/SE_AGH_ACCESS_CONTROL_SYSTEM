import threading
import cv2
import numpy as np
import time
import platform
from enum import Enum
from pyzbar.pyzbar import decode
from sqlalchemy import text, insert
from app.core.database import SessionLocal
from app.services.facial_recognition import train_lbph_from_db, recognize_and_annotate_frame
from app.models.qr_image import unauthorized_access, good_entries

class CameraState(Enum):
    IDLE = "IDLE"
    QR_SCANNING = "QR_SCANNING"
    FACE_VERIFICATION = "FACE_VERIFICATION"
    ACCESS_GRANTED = "ACCESS_GRANTED"
    ACCESS_DENIED = "ACCESS_DENIED"

class VideoCamera:
    def __init__(self):
        self.video = None
        self.lock = threading.Lock()
        
        # --- PRÓBA OTWARCIA KAMERY (Skanowanie indeksów) ---
        # --- STAN SYSTEMU ---
        self.state = CameraState.IDLE
        self.state_start_time = 0
        
        # --- DANE SESJI ---
        self.target_employee = None
        self.verified_employee = None
        self.last_qr_text = None
        
        # Flagi wyników
        self.qr_verified = False
        self.face_verified = False
        self.face_blocked = False
        
        # Liczniki
        self.face_failed_attempts = 0
        self.unauthorized_logged = False
        
        # Cache
        self.last_detection_time = 0
        self.face_model = None
        self.face_model_loaded_at = 0.0
        self.frame_count = 0
        self.process_every_n_frames = 4

        self.last_open_attempt_time = 0
        
    def _open_camera(self):
        """Prywatna metoda do otwierania kamery."""
        # Zabezpieczenie przed spamowaniem próbami otwarcia (max raz na 2 sekundy)
        if time.time() - self.last_open_attempt_time < 2.0:
            return

        self.last_open_attempt_time = time.time()
        backend =  cv2.CAP_ANY
        
        # Próbujemy tylko /dev/video0 dla uproszczenia (lub pętlą jeśli wolisz)
        for index in range(2): 
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    print(f"Kamera otwarta (index={index})")
                    self.video = cap
                    return
                else:
                    cap.release()
        
        print("Nie udało się otworzyć kamery (Auto-Retry)")

    def __del__(self):
            if self.video.isOpened():
                self.video.release()

    def reset_to_idle(self):
        with self.lock:
            self._reset_session_state()
            self.state = CameraState.IDLE
            self.state_start_time = time.time()
            print("Camera reset to IDLE state")
    def start_qr_scanning(self):
        with self.lock:
            self._reset_session_state()
            self.state = CameraState.QR_SCANNING
            self.state_start_time = time.time()
            print("Started QR scanning mode")
        
    def set_target_employee(self, employee_name: str):
        with self.lock:
            self.target_employee = employee_name
            self.state = CameraState.FACE_VERIFICATION
            self.face_failed_attempts = 0
            self.state_start_time = time.time()
            print(f"Target employee set to: {employee_name}, switched to FACE_VERIFICATION mode")

    def _reset_session_state(self):
        """Czyści zmienne sesyjne (prywatna metoda)."""
        self.qr_verified = False
        self.face_verified = False
        self.target_employee = None
        self.verified_employee = None
        self.face_blocked = False
        self.face_failed_attempts = 0
        self.unauthorized_logged = False

    def get_qr_status(self):
        return {
            "verified": self.qr_verified,
            "employee": self.verified_employee
        }

    def get_face_status(self):
        return {
            "verified": self.face_verified,
            "employee": self.verified_employee, # Tutaj przechowujemy wynik matchowania
            "target": self.target_employee,
            "blocked": self.face_blocked
        }

    def get_raw_frame(self):
        """
        To jest serce 'Leniwego Ładowania'.
        Jeśli kamera nie działa, spróbuj ją włączyć TERAZ.
        """
        with self.lock:
            # 1. Jeśli nie ma uchwytu wideo lub jest zamknięty -> Otwórz
            if self.video is None or not self.video.isOpened():
                self._open_camera()
            
            # 2. Jeśli nadal None (bo się nie udało), zwróć None
            if self.video is None or not self.video.isOpened():
                return None

            # 3. Pobierz klatkę
            success, image = self.video.read()
            if not success:
                # Jeśli błąd odczytu, zamknij i spróbuj ponownie przy następnym wywołaniu
                self.video.release()
                self.video = None
                return None
                
            return image

    def get_jpg_frame(self):
        """Pobiera klatkę przetworzoną (z ramkami) jako JPEG (dla streamu)."""
        frame = self.get_raw_frame()
        if frame is None:
            return None
        
        if self.state == CameraState.IDLE:
            cv2.putText(frame, "Camera Idle", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            
        elif self.state == CameraState.QR_SCANNING:
            frame = self.process_qr_logic(frame)

        elif self.state == CameraState.FACE_VERIFICATION:
            # Tutaj był błąd: przekazywałeś 'processed_frame', którego nie było.
            # Teraz przekazujemy 'frame', który zdefiniowaliśmy na początku.
            frame = self.process_face_logic(frame)
            
        elif self.state in [CameraState.ACCESS_GRANTED, CameraState.ACCESS_DENIED]:
            self._draw_result_overlay(frame)
            if time.time() - self.state_start_time > 3.0:
                self.start_qr_scanning()

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()
    
    def process_qr_logic(self, frame):
            objects = decode(frame)
            for obj in objects:
                qr_text = obj.data.decode('utf-8')
                self.last_qr_text = qr_text
                
                employee_name = find_employee_by_qr_data(qr_text)
                
                if employee_name and employee_name != "Not Found":
                    self.qr_verified = True
                    self.verified_employee = employee_name
                
                pts = obj.polygon
                if pts:
                    pts = np.array([(int(pt.x), int(pt.y)) for pt in pts], np.int32)
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
                
                if employee_name != "Not Found":
                    cv2.putText(frame, f"Employee: {employee_name}", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                    self.set_target_employee(employee_name)
                    self.qr_verified = True
                    self.verified_employee = employee_name
                else:
                    cv2.putText(frame, "QR Not in Database", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            return frame
    
    def process_face_logic(self, frame):
            current_time = time.time()
            
            if self.face_model is None or (current_time - self.face_model_loaded_at) > 10:
                try:
                    self.face_model = train_lbph_from_db()
                    self.face_model_loaded_at = current_time
                except Exception as e:
                    print(f"Error training model: {e}")
                    cv2.putText(frame, "No face data in DB", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    return frame
            
            recognizer, known_names = self.face_model
            
            if self.face_blocked:
                blocked_frame = frame.copy()
                cv2.putText(blocked_frame, "ACCESS BLOCKED", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                cv2.putText(blocked_frame, "Restart from QR scan", (10, 95),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                return blocked_frame
            
            detected_name, confidence, annotated_frame, face_count = recognize_and_annotate_frame(
                frame,
                recognizer=recognizer,
                known_names=known_names,
                threshold=80.0,
                now=current_time
            )
            
            if detected_name == self.target_employee:
                self.state = CameraState.ACCESS_GRANTED
                self.state_start_time = current_time
                self.face_verified = True
                self.verified_employee = detected_name
                _log_good_entry(employee_name=detected_name)
                cv2.putText(annotated_frame, f"✓ MATCH: {detected_name}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            elif detected_name != "Unknown" or (face_count > 0 and detected_name == "Unknown"):
                self.face_failed_attempts += 1
                cv2.putText(annotated_frame, f"✗ Wrong person: {detected_name}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                cv2.putText(annotated_frame, f"Expected: {self.target_employee}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                if self.face_failed_attempts >= 20:
                    self.face_blocked = True
                    self.state = CameraState.ACCESS_DENIED
                    self.state_start_time = current_time
                    if not self.unauthorized_logged:
                        _log_unauthorized_access(self.last_qr_text, frame)
                        self.unauthorized_logged = True
            return annotated_frame
    
    def _draw_result_overlay(self, frame):
            if self.state == CameraState.ACCESS_GRANTED:
                cv2.putText(frame, "ACCESS GRANTED", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
            elif self.state == CameraState.ACCESS_DENIED:
                cv2.putText(frame, "ACCESS DENIED", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)

try:
    camera_instance = VideoCamera()
except Exception as e:
    print(f"Error initializing camera: {e}")
    camera_instance = None

def find_employee_by_qr_data(qr_text: str) -> str:
    db = SessionLocal()
    try:
        result = db.execute(
            text("SELECT emp_name FROM employees WHERE emp_name LIKE :search"),
            {"search": f"%{qr_text}%"}
        ).first()
        
        if result:
            return result[0]
        return "Not Found"
    finally:
        db.close()

def _log_unauthorized_access(qr_text: str | None, frame_bgr: np.ndarray) -> None:
    db = SessionLocal()
    try:
        ok, buffer = cv2.imencode('.jpg', frame_bgr)
        photo_bytes = buffer.tobytes() if ok else None
        stmt = insert(unauthorized_access).values(
            qr_text=qr_text,
            photo=photo_bytes,
        )
        db.execute(stmt)
        db.commit()
        print(f"Unauthorized access logged (qr_text={qr_text!r})")
    except Exception as e:
        db.rollback()
        print(f"Failed to log unauthorized access: {e}")
    finally:
        db.close()


def _log_good_entry(employee_name: str) -> None:
    db = SessionLocal()
    try:
        emp_id = db.execute(
            text("SELECT emp_id FROM employees WHERE emp_name = :name ORDER BY emp_id DESC LIMIT 1"),
            {"name": employee_name},
        ).scalar()
        stmt = insert(good_entries).values(
            emp_id=emp_id,
            emp_name=employee_name,
        )
        db.execute(stmt)
        db.commit()
        print(f"Good entry logged (employee={employee_name!r})")
    except Exception as e:
        db.rollback()
        print(f"Failed to log good entry: {e}")
    finally:
        db.close()

def generate_frames():
    while True:
        if camera_instance:
            frame_bytes = camera_instance.get_jpg_frame()
            if frame_bytes:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03) # Ważne dla CPU!
        else:
            time.sleep(1) # Czekaj na kamerę
