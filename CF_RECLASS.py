# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 15:14:49 2025

@author: rasmit10
"""

from dotenv import load_dotenv
from pathlib import Path
import os
import requests

# -----------------------------------------------------------
# LOAD ENVIRONMENT
# -----------------------------------------------------------

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")
if not all([ACCOUNT_ID, AUTH_EMAIL, AUTH_KEY]):
    raise EnvironmentError("Missing CF_ACCOUNT_ID or CLOUDFLARE_EMAIL or CLOUDFLARE_API_KEY in .env")

POSTFIX_ID = "4dSd1n3JVjz16PyJ"         # <-- change this
DISPOSITION = "MALICIOUS"                    # NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate/{POSTFIX_ID}/reclassify"

body = {
    "account_id": ACCOUNT_ID,
    "expected_disposition": DISPOSITION
}

headers = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}



r = requests.post(url, headers=headers, json=body)
print(r.json())
print("URL:", url)
print("Request headers:", headers)
print("Body:", body)