# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 11:22:12 2025

Cloudflare - Email Preview

@author: rasmit10
"""


import os
import sys
import json
import base64
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load env vars
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not ACCOUNT_ID or not AUTH_EMAIL or not AUTH_KEY:
    print("Missing env variables.")
    sys.exit(1)

POSTFIX_ID = input("Enter postfix_id: ").strip()
if not POSTFIX_ID:
    print("No postfix_id provided.")
    sys.exit(1)

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate/{POSTFIX_ID}/preview"

headers = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Accept": "application/json",
}

resp = requests.get(url, headers=headers)

try:
    data = resp.json()
except:
    print("Non-JSON response:")
    print(resp.text)
    sys.exit(1)

print("\n=== FULL JSON RESPONSE ===")
print(json.dumps(data, indent=2))

# FIX: screenshot is inside data["result"]
result = data.get("result", {})
screenshot_b64 = result.get("screenshot")

if not screenshot_b64:
    print("\nNo screenshot field found inside result.")
    sys.exit(0)

print("\nScreenshot found! Base64 length:", len(screenshot_b64))
print("\n===== BASE64 START =====")
print(screenshot_b64[:200] + "... (truncated)")  # keep IDE clean
print("===== BASE64 END =====\n")

# Optional: save to file
save = input("Save PNG file? (y/n): ").strip().lower()
if save == "y":
    png_bytes = base64.b64decode(screenshot_b64)
    out_file = f"{POSTFIX_ID}_preview.png"
    with open(out_file, "wb") as f:
        f.write(png_bytes)
    print(f"Saved PNG to {out_file}")

