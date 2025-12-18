from fastapi import APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from app.services.video import generate_frame, generate_face_frame, initialize_camera
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


@router.get('/facerec')
async def read_facerec():
    return FileResponse('app/templates/facerec.html')

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


@router.get('/face_feed')
async def face_feed():
    cap = initialize_camera()
    if cap is None:
        raise HTTPException(status_code=503, detail="Camera not available")

    return StreamingResponse(
        generate_face_frame(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )

@router.get('/dashboard')
async def read_dashboard():
    return FileResponse('app/templates/dashboard.html')
