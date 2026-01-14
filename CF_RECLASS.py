# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 15:14:49 2025

@author: rasmit10
"""
import requests

import CFScriptConfig as CFG

# -----------------------------------------------------------
# LOAD ENVIRONMENT
# -----------------------------------------------------------


POSTFIX_ID = "4dSd1n3JVjz16PyJ"         # <-- change this
DISPOSITION = "MALICIOUS"                    # NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS

url = CFG.API_BASE_URL + f"/investigate/{POSTFIX_ID}/reclassify"

body = {
    "account_id": CFG.ACCOUNT_ID,
    "expected_disposition": DISPOSITION
}

headers = {
    "X-Auth-Email": CFG.AUTH_EMAIL,
    "X-Auth-Key": CFG.AUTH_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}



r = requests.post(url, headers=headers, json=body)
print(r.json())
print("URL:", url)
print("Request headers:", headers)
print("Body:", body)