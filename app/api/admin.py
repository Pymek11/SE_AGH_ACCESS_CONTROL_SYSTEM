from fastapi import APIRouter, HTTPException, status, Header
from fastapi.responses import FileResponse
import base64

router = APIRouter(prefix="/admin", tags=["admin"])

# Demo credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin1"

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
    # For now, just return dashboard without strict verification
    # Later you can add: username = verify_admin_header(authorization)
    return FileResponse('app/templates/dashboard.html')