import asyncio
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from app.services.video import camera_instance, generate_frames, CameraState
from fastapi import HTTPException

router = APIRouter()

@router.get('/')
async def read_root():
    if camera_instance:
        camera_instance.reset_to_idle()

    response = FileResponse('app/templates/index.html')
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    return response


@router.get('/login')
async def read_login():
    return FileResponse('app/templates/login.html')

@router.get('/qr')
async def read_qr():
    if camera_instance:
        camera_instance.start_qr_scanning()
    return FileResponse('app/templates/qr.html')

@router.get('/facerec')
async def read_facerec():
    if not camera_instance or not camera_instance.target_employee:
        print("⚠️ Brak target_employee, przekierowanie do QR")
        return RedirectResponse(url='/qr')
    
    print(f"✅ Face recognition page for: {camera_instance.target_employee}")
    return FileResponse('app/templates/facerec.html')


@router.get('/accessgranted')
async def read_accessgranted():
    return FileResponse('app/templates/accessgranted.html')

@router.get('/accessdenied')
async def read_accessdenied():
    return FileResponse('app/templates/accessdenied.html')


@router.get('/api/qr-status')
async def qr_verification_status():
    if not camera_instance:
        return JSONResponse(
            status_code=503,
            content={"error": "Camera not initialized"}
        )
    status = camera_instance.get_qr_status()
    if status["verified"]:
        print(f"✅ QR Verified: {status['employee']}")
        return JSONResponse(status_code=200, content=status)
    return JSONResponse(status_code=200, content={"verified": False})


@router.post('/api/qr-reset')
async def qr_reset():
    if camera_instance:
        camera_instance.start_qr_scanning()
    return {"success": True, "message": "QR status reset"}

@router.get('/api/face-status')
async def face_verification_status():
    if not camera_instance:
        return JSONResponse(
            status_code=503,
            content={"error": "Camera not initialized"}
        )
    status = camera_instance.get_face_status()
    if status["verified"]:
        print(f"✅ Face Verified: {status['employee']}")
        return JSONResponse(status_code=200, content=status)
    if status["blocked"]:
        return JSONResponse(status_code=403, content={"error": "Access Blocked", "blocked": True})
    
    return JSONResponse(status_code=200, content={"verified": False})


@router.post('/api/face-reset')
async def face_reset():
    if camera_instance:
        camera_instance.start_qr_scanning()
    return {"success": True, "message": "Reset to QR scanning mode"}

@router.post('/api/start-scan')
async def start_scan():
    if camera_instance:
        camera_instance.start_qr_scanning()
    return {"success": True, "message": "Started QR scanning"}

@router.post('/api/stop-scan')
async def stop_scan():
    if camera_instance:
        camera_instance.reset_to_idle()
    return {"success": True, "message": "Stopped scanning"}

@router.get('/video_feed')
async def video_feed():
    if camera_instance is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    return StreamingResponse(
        generate_frames(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )