import asyncio
from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from app.services.video import generate_frame, generate_face_frame, initialize_camera
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from app.services.video import generate_frame, initialize_camera, get_verification_status, reset_verification_status, get_face_verification_status,reset_face_verification_status,set_target_employee,get_target_employee
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

@router.get('/facerec')
async def read_facerec():
    target = get_target_employee()
    if not target:
        print("⚠️ No target employee set, redirecting to QR")
        return RedirectResponse(url='/qr')
    print(f"✅ Face recognition page for: {target}")
    return FileResponse('app/templates/facerec.html')

@router.get('/api/qr-status')
async def qr_verification_status():

    print("⏳ Waiting for QR verification...")
    
    while True:
        status = get_verification_status()
        
        if status["verified"]:
            employee = status["employee"]
            print(f"✅ QR Verified: {status['employee']}")
            set_target_employee(employee)            

            asyncio.create_task(auto_reset_qr_status())

            # Zwróć 200 - QR zweryfikowany!
            return JSONResponse(
                status_code=200,
                content={
                    "verified": True,
                    "employee": status["employee"]
                }
            )
        
        # Czekaj 0.5s przed następnym sprawdzeniem
        await asyncio.sleep(0.5)

async def auto_reset_qr_status():
    await asyncio.sleep(3)
    reset_verification_status()
    print("🔄 QR status auto-reset after 3 seconds")

@router.post('/api/qr-reset')
async def qr_reset():
    reset_verification_status()
    return {"success": True, "message": "QR status reset"}

@router.get('/api/face-status')
async def face_verification_status():
    print("⏳ Waiting for face verification...")
    
    while True:
        status = get_face_verification_status()
        
        if status["verified"]:
            print(f"✅ Face Verified: {status['employee']}")
            
            # Auto-reset po 3 sekundach
            asyncio.create_task(auto_reset_face_status())
            
            # ✅ Zwróć 200 OK gdy twarz zweryfikowana
            return JSONResponse(
                status_code=200,
                content={
                    "verified": True,
                    "employee": status["employee"],
                    "target": status["target"]
                }
            )
        
        await asyncio.sleep(0.5)


async def auto_reset_face_status():
    await asyncio.sleep(3)
    reset_face_verification_status()
    print("🔄 Face status auto-reset after 3 seconds")

@router.post('/api/face-reset')
async def face_reset():
    reset_face_verification_status()
    return {"success": True, "message": "Face status reset"}


# @router.get("/redirect")
# async def redirectface():
#     target = get_target_employee()
    
#     if target:
#         print(f"🎯 Redirecting to face recognition for: {target}")
#     else:
#         print("⚠️ No target employee, redirecting to QR")
#         return RedirectResponse(url='/qr')
    
#     return RedirectResponse(url='/facerec')