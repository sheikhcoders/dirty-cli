import json
import requests

class PlanActAgent:
    def __init__(self, api_url):
        self.api_url = api_url

    def run_command(self, command):
        resp = requests.post(f"{self.api_url}/shell/exec", json={"command": command})
        return resp.json()

    def read_file(self, path):
        resp = requests.get(f"{self.api_url}/file/read", params={"path": path})
        return resp.json()

    def write_file(self, path, content):
        resp = requests.post(f"{self.api_url}/file/write", json={"path": path, "content": content})
        return resp.json()

    def process(self, user_input):
        yield {"type": "plan", "content": f"Analyzing request: {user_input}"}

        yield {"type": "act", "content": "Checking current directory contents..."}
        obs = self.run_command("ls -la")
        yield {"type": "observation", "content": obs.get("stdout") if obs else "Error executing command"}

        yield {"type": "act", "content": "Creating a summary report..."}
        self.write_file("/sandbox/report.txt", f"Agent processed: {user_input}\nResults: Success")

        yield {"type": "done", "content": "Mission accomplished. Report created at /sandbox/report.txt"}
