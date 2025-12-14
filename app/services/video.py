import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2
import numpy as np
import time
from pyzbar.pyzbar import decode
from sqlalchemy import text
from app.core.database import SessionLocal

# Global state for video capture
_cap = None
_last_detection_time = 0

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
    employee_name = None
    
    decoded_objects = decode(frame)
    
    for obj in decoded_objects:
        qr_text = obj.data.decode('utf-8')
        employee_name = find_employee_by_qr_data(qr_text)
        
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
