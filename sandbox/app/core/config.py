import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sandbox-api")

class Settings:
    PROJECT_NAME: str = "AI Agent Sandbox"
    API_V1_STR: str = "/api/v1"

settings = Settings()
