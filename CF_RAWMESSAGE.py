# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 10:47:16 2025

@author: rasmit10
"""

# -*- coding: utf-8 -*-
"""
Fetch raw EML for one Cloudflare postfix_id
"""

import requests
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# -----------------------------------------------------------
# LOAD ENVIRONMENT (.env must contain CF_ACCOUNT_ID, CLOUDFLARE_EMAIL, CLOUDFLARE_API_KEY)
# -----------------------------------------------------------
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not ACCOUNT_ID or not AUTH_EMAIL or not AUTH_KEY:
    print("Missing required environment variables in .env file.")
    sys.exit(1)

# -----------------------------------------------------------
# USER INPUT — one postfix ID
# -----------------------------------------------------------

POSTFIX_ID = input("Enter postfix_id: ").strip()

if not POSTFIX_ID:
    print("No postfix_id entered. Exiting.")
    sys.exit(1)

# -----------------------------------------------------------
# API REQUEST
# -----------------------------------------------------------
url = f"https://api.cloudflare.com/client/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate/{POSTFIX_ID}/raw"

headers = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Accept": "message/rfc822",   # asks for raw EML
}

print(f"\nRequesting raw EML for {POSTFIX_ID}...\n")

resp = requests.get(url, headers=headers)

# -----------------------------------------------------------
# HANDLE RESPONSE
# -----------------------------------------------------------
if resp.status_code == 200:
    print("===== RAW EML START =====\n")
    try:
        # Decode as text; EML headers are ASCII-safe
        print(resp.content.decode("utf-8", errors="replace"))
    except:
        print(resp.text)
    print("\n===== RAW EML END =====")
else:
    print(f"HTTP {resp.status_code} ERROR")
    try:
        print(resp.json())
    except:
        print(resp.text)
