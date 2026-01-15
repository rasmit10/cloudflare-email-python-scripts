# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 15:14:49 2025

@author: rasmit10
"""
import requests

import CFScriptConfig as CFG

def reclassify_message(postfix_id, disposition):
    VALID_DISPOSITIONS=["NONE", "BULK", "MALICIOUS", "SPAM", "SPOOF", "SUSPICIOUS"]
    
    if(not disposition.upper() in VALID_DISPOSITIONS):
        print("[error] invalid disposition provided. Disposition needs to be one of the following: NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS")
        return None
        
    url = CFG.API_BASE_URL + f"/investigate/{postfix_id}/reclassify"

    body = {
        "expected_disposition": disposition.upper()
    }

    headers = {
        "X-Auth-Email": CFG.AUTH_EMAIL,
        "X-Auth-Key": CFG.AUTH_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    print(f"Making request to {url} with body {body}")
    r = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)
    return r

if __name__ == "__main__":
    POSTFIX_ID = "4dSd1n3JVjz16PyJ"         # <-- change this
    DISPOSITION = "MALICIOUS"                    # NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS

    r = reclassify_message(POSTFIX_ID, DISPOSITION)
    print(r.json())
