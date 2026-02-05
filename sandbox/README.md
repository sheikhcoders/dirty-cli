# AI Agent Sandbox

Isolated execution environment based on Docker containers.

## Features
- **Shell**: Secure command execution.
- **File**: Read/Write/Delete operations.
- **Browser**: Google Chrome with VNC/NoVNC access.
- **Process Management**: Supervisor integration.

## API Usage
- Shell: `POST /api/v1/shell/exec`
- File: `GET /api/v1/file/read`, `POST /api/v1/file/write`
- Supervisor: `GET /api/v1/supervisor/status`

## Graphical Access
VNC is available via NoVNC on port 6080.
