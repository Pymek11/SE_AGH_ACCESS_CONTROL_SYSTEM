from fastapi import APIRouter
from fastapi.responses import FileResponse
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