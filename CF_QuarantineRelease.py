# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 12:42:52 2025

CLOUDLFARE - RELEASE FROM QUARANTINE

@author: rasmit10
"""

import requests
import json
import sys

import CFSearchConfig as CFG

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

url = CFG.API_BASE_URL + f"/investigate/release"

headers = {
    "X-Auth-Email": CFG.AUTH_EMAIL,
    "X-Auth-Key": CFG.AUTH_KEY,
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
