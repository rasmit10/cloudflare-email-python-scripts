# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 09:00:35 2025

Cloudflare BULK MOVE

@author: rasmit10
"""

import time
import csv
import json
from pathlib import Path

import CFScriptConfig as CFG


# -----------------------------
# CONFIG — EDIT THESE
# -----------------------------
DESTINATION = "RecoverableItemsDeletions"     # Options["Inbox", "JunkEmail", "DeletedItems", "RecoverableItemsDeletions", "RecoverableItemsPurges"]

INPUT_FILE = r"inputfile.csv " #<---change this
OUTPUT_FILE = "outputfile.csv" #<---change this

# -----------------------------

def read_postfix_id_csv(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    ids = []
    with open(path, newline="", encoding="utf-8") as cf:
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

def bulk_move(destination, in_file, out_file):
    url = CFG.API_BASE_URL + "/investigate"
    
    # Read postfix IDs
    postfix_ids = read_postfix_id_csv(in_file)

    print(f"Loaded {len(postfix_ids)} postfix IDs")


    # Prepare CSV output
    fieldnames = ["postfix_id", "http_status", "success", "error", "raw_response"]
    with open(out_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Process each ID one-by-one
        for postfix_id in postfix_ids:
            print(f"Moving {postfix_id} → {destination} ... ")

            url = f"{url}/{postfix_id}/move"
            body = {"destination": destination}

            success = ""
            error_msg = ""
            data = {}

            for attempt in range(CFG.MAX_RETRIES):
                print(f'Attempt {attempt} ... ', end=" ")
                response = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)

                if response.status_code == 200:
                    try:
                        data = response.json()
                    except:
                        data = {"error": "Non-JSON response", "raw": response.text}

                    success = data.get("success", False)
                    error_msg = None
                    print("OK\n")

                    # Cloudflare may return errors inside 'errors'
                    if isinstance(data, dict) and "errors" in data and data["errors"]:
                        error_msg = json.dumps(data["errors"])
                        time.sleep((2 ** attempt) * 0.5 + CFG.RATE_LIMIT_SLEEP)
                        continue
                    if success:
                        break
                elif response.status_code in (404, 422):
                    print(f"FAILED: {response.status_code} - permanent failure, no retry.")
                    error_msg = f"{response.status_code} - permanent failure, no retry."
                    break   
                else:
                    print(f"FAILED: {response.status_code}")
                    time.sleep((2 ** attempt) * 0.5 + CFG.RATE_LIMIT_SLEEP)
                    continue

                
                

            # Write row
            writer.writerow({
                "postfix_id": postfix_id,
                "http_status": response.status_code,
                "success": success,
                "error": error_msg,
                "raw_response": json.dumps(data)
            })

    print(f"\nDone! Results written to {out_file}")

if __name__ == "__main__":
    bulk_move(DESTINATION, INPUT_FILE, OUTPUT_FILE)


