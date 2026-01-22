import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# ---------------------------
# CONFIG / TUNABLES
# ---------------------------
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not all((ACCOUNT_ID, AUTH_EMAIL, AUTH_KEY)):
    raise EnvironmentError("Missing CF_ACCOUNT_ID or CLOUDFLARE_EMAIL or CLOUDFLARE_API_KEY in environment or .env")

API_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security"

API_MAX_PER_PAGE = 1000
PER_PAGE = 1000      # Cloudflare limit
TIMEOUT = 90
MAX_RETRIES = 5
SLEEP_BETWEEN_REQUESTS = 0.05
RATE_LIMIT_SLEEP = 1.0

# Safety caps
MAX_TOTAL_REQUESTS = 200000
MAX_RECURSION_DEPTH = 40

# Chunking settings
MIN_CHUNK_SECONDS = 0.001   # 1 ms
MICRO_SUBSLICES = 10

# Debug & checkpoint folder
DEBUG_DIR = Path(__file__).resolve().parent / "debug"
DEBUG_DIR.mkdir(exist_ok=True)
MSGID_PROGRESS = DEBUG_DIR / "msgid_progress.json"

# Default delay between each message-id query (no prompt)
DELAY_BETWEEN_IDS = 0.2

# HTTP session
session = requests.Session()
session.headers.update({
            "Authorization": f"Bearer {AUTH_KEY}",
            "Accept": "application/json",
})