# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 12:59:34 2025

Cloudflare Block Sender

@author: rasmit10
"""


# -*- coding: utf-8 -*-
"""
Simple script to block a sender, domain, or IP in Cloudflare Email Security.
Prompts user for pattern, pattern_type, and case number.
"""

import os
import sys
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# -----------------------------------------------------------
# LOAD ENVIRONMENT
# -----------------------------------------------------------

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not ACCOUNT_ID or not AUTH_EMAIL or not AUTH_KEY:
    print("Missing required environment variables in .env.")
    sys.exit(1)

# -----------------------------------------------------------
# API BASE + SESSION
# -----------------------------------------------------------

SETTINGS_BASE = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/settings"

session = requests.Session()
session.headers.update({
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Content-Type": "application/json"
})

# -----------------------------------------------------------
# USER INPUTS
# -----------------------------------------------------------

pattern = input("Enter sender / domain / IP to block: ").strip()
if not pattern:
    print("No pattern entered. Exiting.")
    sys.exit(1)

case_number = input("Enter case number: ").strip()
if not case_number:
    print("No case number entered. Exiting.")
    sys.exit(1)

print("\nChoose pattern type:")
print("  1 = EMAIL   (example: user@example.com)")
print("  2 = DOMAIN  (example: badsite.com)")
print("  3 = IP      (example: 192.168.1.10)")
print("  4 = UNKNOWN (rare — only if unsure)")

ptype = input("Enter 1, 2, 3, or 4: ").strip()

if ptype == "1":
    pattern_type = "EMAIL"
elif ptype == "2":
    pattern_type = "DOMAIN"
elif ptype == "3":
    pattern_type = "IP"
elif ptype == "4":
    pattern_type = "UNKNOWN"
else:
    print("Invalid choice. Defaulting to EMAIL.")
    pattern_type = "EMAIL"

# Cloudflare handles regex internally — NO regex flag needed
is_regex = False

comment = f"{datetime.utcnow().strftime('%Y/%m/%d')} - {case_number}"

body = {
    "pattern": pattern,
    "pattern_type": pattern_type,
    "is_regex": is_regex,
    "comments": comment
}

# -----------------------------------------------------------
# SEND API REQUEST
# -----------------------------------------------------------

url = f"{SETTINGS_BASE}/block_senders"
resp = session.post(url, json=body, timeout=10)

if resp.status_code not in (200, 201):
    print("\n❌ Failed to create blocked sender:")
    print(resp.text)
    sys.exit(1)

result = resp.json().get("result")

# -----------------------------------------------------------
# OUTPUT
# -----------------------------------------------------------

print("\n✅ Block created successfully!")
print("------------------------------")
print(f"Pattern     : {result.get('pattern')}")
print(f"Type        : {result.get('pattern_type')}")
print(f"Is Regex    : {result.get('is_regex')}")
print(f"Comments    : {result.get('comments')}")
print(f"Created ID  : {result.get('id')}")
print("------------------------------")
