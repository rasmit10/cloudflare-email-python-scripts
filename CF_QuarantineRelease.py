# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 12:42:52 2025

CLOUDLFARE - RELEASE FROM QUARANTINE

@author: rasmit10
"""

import requests
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# -----------------------------------------------------------
# LOAD ENV 
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
# USER CONFIG — TXT INPUT FILE
# -----------------------------------------------------------

INPUT_FILE = r"C:\Users\rasmit10\Dropbox\PC\Documents\quarantinerelease.txt" # EDIT THIS

# -----------------------------------------------------------

# Read postfix IDs from file
try:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        postfix_ids = [line.strip() for line in f if line.strip()]
except Exception as e:
    print(f"Could not read file: {e}")
    sys.exit(1)

if not postfix_ids:
    print("No postfix IDs found in input file.")
    sys.exit(1)

print(f"Loaded {len(postfix_ids)} postfix IDs.")
print("Releasing from quarantine...\n")

# -----------------------------------------------------------
# API REQUEST
# -----------------------------------------------------------

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate/release"

headers = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Content-Type": "application/json",
}

# Cloudflare expects: ["id1", "id2", "id3"]
payload = postfix_ids

resp = requests.post(url, headers=headers, json=payload)

# Attempt to decode JSON
try:
    data = resp.json()
except:
    print("Non-JSON response from Cloudflare:")
    print(resp.text)
    sys.exit(1)

print(f"HTTP {resp.status_code}")
print("\n=== FULL JSON RESPONSE ===")
print(json.dumps(data, indent=2))

# -----------------------------------------------------------
# SIMPLE SUMMARY
# -----------------------------------------------------------

result = data.get("result", [])

print("\n=== RELEASE SUMMARY ===\n")

if isinstance(result, dict):
    result = [result]  # Cloudflare might return a single object

for entry in result:
    pid = entry.get("postfix_id", "<unknown>")
    delivered = entry.get("delivered") or []
    failed = entry.get("failed") or []
    undelivered = entry.get("undelivered") or []

    print(f"Postfix ID: {pid}")
    print(f"  Delivered   : {len(delivered)}")
    print(f"  Failed      : {len(failed)}")
    print(f"  Undelivered : {len(undelivered)}\n")

print("Done.")
