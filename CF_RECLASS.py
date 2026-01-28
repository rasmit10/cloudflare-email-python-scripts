# -*- coding: utf-8 -*-
"""
Created on Tue Dec  2 15:14:49 2025

@author: rasmit10
"""
import requests
from pathlib import Path
import csv

import CFScriptConfig as CFG

def read_postfix_id_csv(path): # pyright: ignore[reportMissingParameterType]
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    ids = []
    with open(path, newline="", encoding="utf-8-sig") as cf:
        reader = csv.reader(cf)
        rows = list(reader)
    if not rows:
        return []
    header = [c.strip().lower() for c in rows[0]]
    candidate_cols = None
    for name in ("postfix_id", "postfix-id", "postfix indent"):
        if name in header:
            candidate_cols = header.index(name)
            start_row = 1
            break
    if candidate_cols is None:
        candidate_cols = 0
        start_row = 0
    for r in rows[start_row:]:
        if len(r) <= candidate_cols:
            continue
        v = r[candidate_cols].strip()
        if v:
            ids.append(v)
    return ids

def reclassify_message(postfix_id=None, disposition=None):
    VALID_DISPOSITIONS=["NONE", "BULK", "MALICIOUS", "SPAM", "SPOOF", "SUSPICIOUS"]
    
    if(not disposition.upper() in VALID_DISPOSITIONS):
        print("[error] invalid disposition provided. Disposition needs to be one of the following: NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS")
        return None
    
    body = {
        "expected_disposition": disposition.upper()
    }  
    url = CFG.API_BASE_URL + f"/investigate/{postfix_id}/reclassify"
    
    print(f"Making request to {url} with body {body}")
    r = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)

    if(r.status_code == 202):
        print(f'\n[success] message submitted with disposition: {disposition}')
    else:
        print(r)

def bulk_reclassify(input_file, num_submissions, disposition):
    body = {
        "expected_disposition": disposition.upper()
    }  
    
    num_successes = 0
    successful_ids = []
    postfix_ids = read_postfix_id_csv(input_file)

    print(f"Loaded {len(postfix_ids)} ids to reclassify. Submitting until {num_submissions} are successful. Expect a lot of errors.")


    for id in postfix_ids:
        url = CFG.API_BASE_URL + f"/investigate/{id}/reclassify"
        r = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)
        if r.status_code == 202:
            num_successes += 1
            successful_ids.append(id)
            print(f"message {id} resubmitted as {disposition}. {num_successes}/{num_submissions} completed.")
        else:
            print(f"failed to resubmit {id} with error {r.json()["errors"][0]["code"]}")
        
        if num_successes >= int(num_submissions):
            print(f"[success] reclassified {successful_ids} as {disposition}")
            break
    if num_successes > 0:
        print(f"[partial success] reclassified {successful_ids} as {disposition}. {num_submissions} of desired {num_submissions} mesasges were submitted.")
    else:
        print("[error] no messages are able to be submitted. Consider uploading a .eml file via the GUI.")

if __name__ == "__main__":
    POSTFIX_ID = "4dSd1n3JVjz16PyJ"         # <-- change this
    DISPOSITION = "MALICIOUS"                    # NONE | BULK | MALICIOUS | SPAM | SPOOF | SUSPICIOUS

    r = reclassify_message(POSTFIX_ID, DISPOSITION)
    print(r.json())
