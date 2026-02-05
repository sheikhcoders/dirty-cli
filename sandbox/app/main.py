from fastapi import FastAPI
from app.api.v1 import shell, file, supervisor

app = FastAPI(title="AI Agent Sandbox API", version="1.0.0")

app.include_router(shell.router, prefix="/api/v1/shell", tags=["shell"])
app.include_router(file.router, prefix="/api/v1/file", tags=["file"])
app.include_router(supervisor.router, prefix="/api/v1/supervisor", tags=["supervisor"])

@app.get("/")
async def root():
    return {"message": "Sandbox API is running"}
