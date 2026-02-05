from pydantic import BaseModel
from typing import Optional, List

class CommandRequest(BaseModel):
    command: str
    cwd: Optional[str] = "/app"
    timeout: Optional[int] = 30

class CommandResponse(BaseModel):
    stdout: str
    stderr: str
    exit_code: int

class FileReadRequest(BaseModel):
    path: str

class FileWriteRequest(BaseModel):
    path: str
    content: str

class FileResponse(BaseModel):
    success: bool
    message: str
    content: Optional[str] = None
