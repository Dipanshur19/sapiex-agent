"""
config.py — Load environment variables and expose them as constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
MODEL_NAME: str = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
STATE_DIR: str = os.getenv("STATE_DIR", ".agent_state")
SKILLS_DIR: str = os.getenv("SKILLS_DIR", "skills")

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set.\n"
        "1. Go to https://console.groq.com/keys\n"
        "2. Create a free API key (no credit card needed)\n"
        "3. Copy .env.example to .env and paste your key: GROQ_API_KEY=gsk_..."
    )
