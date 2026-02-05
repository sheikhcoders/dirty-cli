from fastapi import APIRouter, HTTPException
import os
from app.schemas.models import FileWriteRequest, FileResponse

router = APIRouter()

@router.get("/read", response_model=FileResponse)
async def read_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "r") as f:
            content = f.read()
        return FileResponse(success=True, message="File read successfully", content=content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/write", response_model=FileResponse)
async def write_file(req: FileWriteRequest):
    try:
        os.makedirs(os.path.dirname(req.path), exist_ok=True)
        with open(req.path, "w") as f:
            f.write(req.content)
        return FileResponse(success=True, message="File written successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete", response_model=FileResponse)
async def delete_file(path: str):
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        os.remove(path)
        return FileResponse(success=True, message="File deleted successfully")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
