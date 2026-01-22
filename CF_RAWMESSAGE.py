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
import sys

import CFSCriptConfig as CFG


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
url = CFG.API_BASE_URL + f"/investigate/{POSTFIX_ID}/raw"

headers = {
    "X-Auth-Email": CFG.AUTH_EMAIL,
    "X-Auth-Key": CFG.AUTH_KEY,
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
