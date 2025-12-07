from fastapi import APIRouter
from fastapi.responses import FileResponse
router = APIRouter()

@router.get('/')
async def read_root():
    return FileResponse('app/templates/index.html')

