import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import cv2
import numpy as np
import time
from pyzbar.pyzbar import decode
from sqlalchemy import text
from app.core.database import SessionLocal


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


cap = cv2.VideoCapture(0)

print("Starting QR Scanner (press 'q' to exit)...")

last_detection_time = 0

while True:
    success, img = cap.read()
    if not success:
        break

    employee_name, annotated_frame = process_qr_code(img)
    
    current_time = time.time()
    if employee_name and employee_name != "Not Found" and (current_time - last_detection_time) > 1:
        print(f"✓ QR Detected: {employee_name}")
        last_detection_time = current_time
    
    cv2.imshow("QR Scanner", annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()