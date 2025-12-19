from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from app.services.video import generate_frame, initialize_camera, get_verification_status, reset_verification_status
from fastapi import HTTPException

router = APIRouter()

@router.get('/')
async def read_root():
    return FileResponse('app/templates/index.html')


@router.get('/login')
async def read_login():
    return FileResponse('app/templates/login.html')

@router.get('/qr')
async def read_qr():
    return FileResponse('app/templates/qr.html')

@router.get('/video_feed')
async def video_feed():
    # Check if camera is available before streaming
    cap = initialize_camera()
    if cap is None:
        raise HTTPException(status_code=503, detail="Camera not available")
    
    return StreamingResponse(
        generate_frame(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@router.get('/dashboard')
async def read_dashboard():
    return FileResponse('app/templates/dashboard.html')

@router.get('/facerec')
async def read_facerec():
    return FileResponse('app/templates/facerec.html')

@router.get('/api/qr-status')
async def qr_verification_status():
    status = get_verification_status()
    if status["verified"]:
        response = Response(status_code=200)
        print(f"✓ QR Verification Status: {status}")
    return response

@router.post('/api/qr-reset')
async def qr_reset():
    reset_verification_status()
    return {"success": True, "message": "QR status reset"}

# @router.get('/api/face-status')
# async def face_status():
#     status = get_face_verification_status()
#     return status

# @router.post('/api/face-reset')
# async def face_reset():
#     reset_face_verification_status()
#     return {"success": True, "message": "Face status reset"}