from fastapi import APIRouter, HTTPException, status, Header, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy import insert, text  # ✅ Jeden import, usuń duplikat
from app.core.database import SessionLocal
from app.models.qr_image import employees
from app.services.qr_generator import generate_qr_code_blob
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
        # ✅ Zmienione: emp_id zamiast id
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
        # ✅ Zmienione: emp_id zamiast id
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