# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 11:18:04 2025

@author: rasmit10
"""


import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# ---- config (you can edit if not using .env) ----
TIMEOUT = 15  # seconds
# -------------------------------------------------

# Load .env from script directory
here = Path(__file__).resolve().parent
load_dotenv(here / ".env")

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not (ACCOUNT_ID and AUTH_EMAIL and AUTH_KEY):
    print("Missing env vars. Ensure .env contains CF_ACCOUNT_ID, CLOUDFLARE_EMAIL, CLOUDFLARE_API_KEY")
    sys.exit(1)

POSTFIX_ID = input("Enter postfix_id: ").strip()
if not POSTFIX_ID:
    print("No postfix_id entered. Exiting.")
    sys.exit(0)

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate/{POSTFIX_ID}/trace"
headers = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Accept": "application/json",
}

print(f"\nRequesting trace for {POSTFIX_ID}...\n")

try:
    resp = requests.get(url, headers=headers, timeout=TIMEOUT)
except requests.RequestException as e:
    print("Request error:", e)
    sys.exit(1)

if resp.status_code == 200:
    try:
        data = resp.json()
    except Exception:
        print("Received 200 but response is not valid JSON. Raw body:\n")
        print(resp.text)
        sys.exit(1)

    # Pretty-print the trace JSON (inbound/outbound etc.)
    print(json.dumps(data, indent=2, ensure_ascii=False))
else:
    # try to show JSON error if present
    print(f"HTTP {resp.status_code} error")
    try:
        err = resp.json()
        print(json.dumps(err, indent=2, ensure_ascii=False))
    except Exception:
        print(resp.text)
