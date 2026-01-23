from fastapi import APIRouter, HTTPException, status, Header, File, UploadFile, Form
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import insert, text  # ✅ Jeden import, usuń duplikat
import cv2
import numpy as np
import base64

from app.core.database import SessionLocal
from app.models.qr_image import employees
from app.services.qr_generator import generate_qr_code_blob
from app.services.facial_recognition import FACE_CASCADE, crop_and_normalize, save_face_to_db
from app.services.video import camera_instance

router = APIRouter(prefix="/admin", tags=["admin"])

# Demo credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1"

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_admin_header(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        credentials = base64.b64decode(authorization.split(" ")[1]).decode()
        username, password = credentials.split(":")
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return username
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")


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
    verify_admin_header(authorization)
    db = SessionLocal()
    
    try:
        # Read face photo as bytes
        face_photo_bytes = await facePhoto.read()
        nparr = np.frombuffer(face_photo_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid image file"
            )
        try:
            face_mask = crop_and_normalize(img)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(e)
            )
        ret, buffer = cv2.imencode('.jpg', face_mask)
        face_photo_bytes = buffer.tobytes()
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
    except HTTPException as he:
        raise he
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
    verify_admin_header(authorization)
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT emp_id, emp_name FROM employees")).fetchall()
        users = [{"id": row[0], "name": row[1]} for row in result]
        return {"users": users}
    finally:
        db.close()

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, authorization: str = Header(None)):
    verify_admin_header(authorization)
    db = SessionLocal()
    try:
        db.execute(text("DELETE FROM employees WHERE emp_id = :id"), {"id": user_id})
        db.commit()
        return {"success": True, "message": f"User {user_id} deleted"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/face-capture")
async def capture_face_from_camera(
    fullName: str = Form(...),
    authorization: str = Header(None),
):
    verify_admin_header(authorization)

    # 1. Bierzemy klatkę z działającej kamery (Singleton)
    if not camera_instance:
        raise HTTPException(status_code=503, detail="Camera service not initialized")

    frame = camera_instance.get_raw_frame()
    
    if frame is None:
        raise HTTPException(status_code=503, detail="Could not capture frame from camera")

    db = SessionLocal()
    try:
        try:
            face_mask = crop_and_normalize(frame)
        except ValueError as e:
            # "Nie wykryto twarzy"
            raise HTTPException(status_code=422, detail=str(e))

        # 3. Kodujemy do JPG (BLOB)
        ret, buffer = cv2.imencode('.jpg', face_mask)
        face_blob = buffer.tobytes()

        # 4. Generujemy QR
        qr_code_blob = generate_qr_code_blob(fullName)

        # 5. Zapisujemy wszystko
        stmt = insert(employees).values(
            emp_name=fullName,
            emp_qr_code=qr_code_blob,
            emp_photo=face_blob,
        )
        db.execute(stmt)
        db.commit()

        return {"success": True, "message": f"User '{fullName}' added with Face & QR."}

    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@router.get('/api/failed-attempts')
async def get_failed_attempts(authorization: str = Header(None)):
    verify_admin_header(authorization)
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT * FROM unauthorized_access")).fetchall()
        attempts = [
            {
                "id": row[0],
                "qr_text": row[1],
                "photo": base64.b64encode(row[2]).decode() if row[2] else None,
                "created_at": row[3]
            } for row in result
        ]
        return {"failed_attempts": attempts}
    finally:
        db.close()
@router.get('/api/access-denials')
async def get_access_denials(authorization: str = Header(None)):
    return FileResponse('app/templates/denials.html')
