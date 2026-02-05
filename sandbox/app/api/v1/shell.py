from fastapi import APIRouter, HTTPException
import subprocess
from app.schemas.models import CommandRequest, CommandResponse

router = APIRouter()

@router.post("/exec", response_model=CommandResponse)
async def execute_command(req: CommandRequest):
    try:
        process = subprocess.run(
            req.command,
            shell=True,
            cwd=req.cwd,
            capture_output=True,
            text=True,
            timeout=req.timeout
        )
        return CommandResponse(
            stdout=process.stdout,
            stderr=process.stderr,
            exit_code=process.returncode
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
