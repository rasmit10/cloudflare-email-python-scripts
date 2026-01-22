# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 11:18:04 2025

@author: rasmit10
"""

import sys
import json
import requests

import CFScriptConfig as CFG


POSTFIX_ID = input("Enter postfix_id: ").strip()
if not POSTFIX_ID:
    print("No postfix_id entered. Exiting.")
    sys.exit(0)

url = CFG.API_BASE_URL + f"/investigate/{POSTFIX_ID}/trace"
headers = {
    "X-Auth-Email": CFG.AUTH_EMAIL,
    "X-Auth-Key": CFG.AUTH_KEY,
    "Accept": "application/json",
}

print(f"\nRequesting trace for {POSTFIX_ID}...\n")

try:
    resp = requests.get(url, headers=headers, timeout=CFG.TIMEOUT)
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
