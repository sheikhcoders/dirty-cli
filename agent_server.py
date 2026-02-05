import docker
import uuid
import json
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict
import aiohttp
from plan_act_agent import PlanActAgent

app = FastAPI(title="Agent Server")
client = docker.from_env()

# In-memory storage for sessions
sessions: Dict[str, dict] = {}

class Session:
    def __init__(self, session_id: str, container):
        self.session_id = session_id
        self.container = container
        self.events = asyncio.Queue()

@app.post("/session/create")
async def create_session():
    session_id = str(uuid.uuid4())
    # Start the Sandbox container
    container_name = f"sandbox-{session_id}"
    container = client.containers.run(
        "agent-sandbox:latest",
        detach=True,
        network="agent-network",
        ports={'8000/tcp': None, '6080/tcp': None}, # Mapped to host for external access
        name=container_name
    )
    # Wait for the container to start and get its ports
    container.reload()
    # For external access (NoVNC), we still need the host port
    vnc_port = container.ports['6080/tcp'][0]['HostPort']

    sessions[session_id] = {
        "id": session_id,
        "container_id": container.id,
        "api_url": f"http://{container_name}:8000/api/v1", # Use internal Docker network
        "vnc_url": f"http://localhost:{vnc_port}",   # URL for the browser/user
        "events": asyncio.Queue()
    }

    return {"session_id": session_id, "vnc_url": sessions[session_id]["vnc_url"]}

@app.post("/session/{session_id}/message")
async def handle_message(session_id: str, payload: dict, background_tasks: BackgroundTasks):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    message = payload.get("message")
    # Forward to PlanAct Agent logic
    background_tasks.add_task(run_agent_loop, session_id, message)
    return {"status": "processing"}

async def run_agent_loop(session_id: str, message: str):
    session = sessions[session_id]
    queue = session["events"]

    agent = PlanActAgent(session['api_url'])

    # Run the agent generator in a separate thread if it was synchronous,
    # but here we'll just iterate over it.
    for event in agent.process(message):
        await queue.put(json.dumps(event))
        await asyncio.sleep(0.5) # Small delay for UI readability

@app.get("/session/{session_id}/events")
async def get_events(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_generator():
        queue = sessions[session_id]["events"]
        while True:
            event = await queue.get()
            yield f"data: {event}\n\n"
            if "done" in event:
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
