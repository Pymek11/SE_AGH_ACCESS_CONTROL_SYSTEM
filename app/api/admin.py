from fastapi import APIRouter, HTTPException, status, Header, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy import insert, text  # ✅ Jeden import, usuń duplikat
from app.core.database import SessionLocal
from app.models.qr_image import employees
from app.services.qr_generator import generate_qr_code_blob
from app.services.facial_recognition import FACE_CASCADE, save_face_to_db
import cv2
import numpy as np
import base64

router = APIRouter(prefix="/admin", tags=["admin"])

# Demo credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_admin_header(authorization: str = Header(None)):
    """Verify admin from Authorization header sent by browser"""
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        # Decode base64 credentials
        credentials = base64.b64decode(authorization.split(" ")[1]).decode()
        username, password = credentials.split(":")
        
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        return username
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@router.get("/dashboard")
async def admin_dashboard(authorization: str = Header(None)):
    return FileResponse('app/templates/dashboard.html')

@router.post("/users")
async def create_user(
    fullName: str = Form(...),
    facePhoto: UploadFile = File(...),
    authorization: str = Header(None)
):
    """Create a new user with face photo and auto-generated QR code"""
    
    db = SessionLocal()
    
    try:
        # Read face photo as bytes
        face_photo_bytes = await facePhoto.read()
        
        # Generate QR code blob from full name
        qr_code_blob = generate_qr_code_blob(fullName)
        
        # Insert into database
        stmt = insert(employees).values(
            emp_name=fullName,
            emp_qr_code=qr_code_blob,
            emp_photo=face_photo_bytes,
        )
        result = db.execute(stmt)
        db.commit()
        
        print(f"✓ Added user: {fullName}")
        print(f"  → Face photo: {len(face_photo_bytes)} bytes")
        print(f"  → QR code: {len(qr_code_blob)} bytes")
        
        return {
            "success": True,
            "message": f"User '{fullName}' added successfully!",
            "user_id": result.lastrowid
        }
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error adding user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding user: {str(e)}"
        )
    finally:
        db.close()

@router.get("/users")
async def list_users(authorization: str = Header(None)):
    """List all users"""
    
    db = SessionLocal()
    
    try:
        result = db.execute(text("SELECT emp_id, emp_name FROM employees")).fetchall()
        users = [{"id": row[0], "name": row[1]} for row in result]  # Zwróć jako 'id' dla JS
        
        return {"users": users}
        
    except Exception as e:
        print(f"✗ Error listing users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )
    finally:
        db.close()

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, authorization: str = Header(None)):
    """Delete a user by ID"""
    
    db = SessionLocal()
    
    try:
        db.execute(text("DELETE FROM employees WHERE emp_id = :id"), {"id": user_id})
        db.commit()
        
        return {"success": True, "message": f"User {user_id} deleted"}
        
    except Exception as e:
        db.rollback()
        print(f"✗ Error deleting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )
    finally:
        db.close()


@router.post("/face-capture")
async def capture_face_from_camera(
    fullName: str = Form(...),
    authorization: str = Header(None),
):
    """Capture a face photo from the server camera and store the face mask in DB.

    This endpoint is meant to be triggered from the live camera view (frontend button).
    It grabs a single frame, detects the largest face, normalizes it to 200x200 grayscale
    and saves it into employees.emp_photo via `save_face_to_db`.

    Expects multipart/form-data with:
    - fullName: str
    """

    # NOTE: we accept Authorization header for future use, but do not enforce it here,
    # because the current /admin pages are served without authenticated HTTP requests.

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Camera not available")

    try:
        # Warm up camera a bit
        frame = None
        for _ in range(5):
            ok, frame = cap.read()
            if ok and frame is not None:
                break

        if frame is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to read frame from camera",
            )

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))
        if len(faces) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No face detected",
            )

        x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))
        face = gray[y : y + h, x : x + w]

        # Normalize exactly like training expects: equalize + resize
        face = cv2.equalizeHist(face)
        face = cv2.resize(face, (200, 200))

        # Persist as the 'mask' used by LBPH training
        save_face_to_db(fullName, face)

        return {
            "success": True,
            "message": f"Face captured for '{fullName}'",
        }
    finally:
        cap.release()