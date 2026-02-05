from fastapi import APIRouter, HTTPException
import subprocess

router = APIRouter()

@router.get("/status")
async def get_status():
    try:
        process = subprocess.run(["supervisorctl", "status"], capture_output=True, text=True)
        return {"status": process.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restart/{service}")
async def restart_service(service: str):
    try:
        process = subprocess.run(["supervisorctl", "restart", service], capture_output=True, text=True)
        return {"message": process.stdout}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
