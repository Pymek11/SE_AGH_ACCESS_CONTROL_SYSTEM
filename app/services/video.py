import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2
import numpy as np
import time
from pyzbar.pyzbar import decode
from sqlalchemy import text
from app.core.database import SessionLocal

from app.services.facial_recognition import train_lbph_from_db, recognize_and_annotate_frame

# Global state for video capture
_cap = None
_last_detection_time = 0
_face_model = None  # (recognizer, known_names)
_face_model_loaded_at = 0.0
_last_face_log_time = 0.0
_qr_verified = False
_verified_employee = None

_face_verified = False
_face_match_employee = None
_target_employee = None  

def initialize_camera():
    global _cap
    if _cap is None:
        _cap = cv2.VideoCapture(0)
    if not _cap.isOpened():
        print("Error: Could not open video device.")
        _cap = None
        return None
    return _cap

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

def process_qr_code(frame):
    global _qr_verified, _verified_employee 
    employee_name = None
    
    decoded_objects = decode(frame)
    
    for obj in decoded_objects:
        qr_text = obj.data.decode('utf-8')
        employee_name = find_employee_by_qr_data(qr_text)

        if employee_name and employee_name != "Not Found":
            _qr_verified = True
            _verified_employee = employee_name
        
        pts = obj.polygon
        if pts:
            pts = np.array([(int(pt.x), int(pt.y)) for pt in pts], np.int32)
            cv2.polylines(frame, [pts], True, (0, 255, 0), 2)
        
        if employee_name != "Not Found":
            cv2.putText(frame, f"Employee: {employee_name}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "QR Not in Database", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    return employee_name, frame

def generate_frame():
    global _last_detection_time
    cap = initialize_camera()
    
    if cap is None:
        error_frame = np.zeros((480, 480, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera not available", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame = buffer.tobytes()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
    try:
        while True:
            success, img = cap.read()
            if not success:
                break

            employee_name, annotated_frame = process_qr_code(img)
            
            # Log detection
            current_time = time.time()
            if employee_name and employee_name != "Not Found" and (current_time - _last_detection_time) > 1:
                print(f"✓ QR Detected: {employee_name}")
                _last_detection_time = current_time
            
            # Encode frame for streaming
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame = buffer.tobytes()
            
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03)
    except Exception as e:
        print(f"Error during video processing: {e}")

def get_verification_status():
    global _qr_verified, _verified_employee
    return {
        "verified": _qr_verified,
        "employee": _verified_employee
    }

def reset_verification_status():
    global _qr_verified, _verified_employee
    _qr_verified = False
    _verified_employee = None

def _get_face_model(max_age_s: float = 10.0):
    global _face_model, _face_model_loaded_at
    now = time.time()
    if _face_model is None or (now - _face_model_loaded_at) > max_age_s:
        _face_model = train_lbph_from_db()
        _face_model_loaded_at = now
    return _face_model

def process_face_recognition(frame):
    global _face_verified, _face_match_employee, _target_employee, _face_model, _face_model_loaded_at, _last_face_log_time
    
    current_time = time.time()
    
    if _face_model is None or (current_time - _face_model_loaded_at) > 10:
        try:
            _face_model = train_lbph_from_db()
            _face_model_loaded_at = current_time
        except Exception as e:
            print(f"Error training model: {e}")
            cv2.putText(frame, "No face data in DB", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            return frame
    
    if _face_model is None:
        cv2.putText(frame, "No face data in DB", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return frame
    
    recognizer, known_names = _face_model
    
    if not _target_employee:
        cv2.putText(frame, "No target employee set", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        return frame
    
    detected_name, confidence, annotated_frame = recognize_and_annotate_frame(
        frame,
        recognizer=recognizer,
        known_names=known_names,
        threshold=80.0,  
        now=current_time
    )
    
    if detected_name and detected_name != "Unknown":
        if detected_name == _target_employee:
            _face_verified = True
            _face_match_employee = detected_name
            
            cv2.putText(annotated_frame, f"✓ MATCH: {detected_name}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            
            if current_time - _last_face_log_time > 1:
                print(f"✅ Face Matched (1:1): {detected_name} == {_target_employee}")
                _last_face_log_time = current_time
        else:
            cv2.putText(annotated_frame, f"✗ Wrong person: {detected_name}", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            cv2.putText(annotated_frame, f"Expected: {_target_employee}", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            if current_time - _last_face_log_time > 1:
                print(f"⚠️ Face mismatch (1:1): Expected {_target_employee}, got {detected_name}")
                _last_face_log_time = current_time
    else:
        cv2.putText(annotated_frame, f"Waiting for: {_target_employee}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    return annotated_frame

def generate_face_frame():
    """Generator dla face recognition feed"""
    cap = initialize_camera()
    
    if cap is None:
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera not available", (50, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ret, buffer = cv2.imencode('.jpg', error_frame)
        frame = buffer.tobytes()
        while True:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    try:
        while True:
            success, img = cap.read()
            if not success:
                break
            
            annotated_frame = process_face_recognition(img)
            
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.03)
            
    except Exception as e:
        print(f"Error during face recognition: {e}")




def get_face_verification_status():
    """Zwraca status weryfikacji twarzy"""
    global _face_verified, _face_match_employee, _target_employee
    return {
        "verified": _face_verified,
        "employee": _face_match_employee,
        "target": _target_employee
    }

def reset_face_verification_status():
    """Resetuje status weryfikacji twarzy"""
    global _face_verified, _face_match_employee, _target_employee
    _face_verified = False
    _face_match_employee = None
    _target_employee = None
    print("🔄 Face verification status reset")

def set_target_employee(employee_name: str):
    """Ustaw pracownika do weryfikacji twarzy"""
    global _target_employee
    _target_employee = employee_name
    print(f"🎯 Target employee set: {employee_name}")

def get_target_employee():
    """Pobierz target employee"""
    global _target_employee
    return _target_employee