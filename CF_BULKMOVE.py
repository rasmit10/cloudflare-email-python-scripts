# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 09:00:35 2025

Cloudflare BULK MOVE

@author: rasmit10
"""

import time
import csv
import json

import CFScriptConfig as CFG


# -----------------------------
# CONFIG — EDIT THESE
# -----------------------------
DESTINATION = "RecoverableItemsDeletions"     # Options["Inbox", "JunkEmail", "DeletedItems", "RecoverableItemsDeletions", "RecoverableItemsPurges"]

INPUT_FILE = r"inputfile.csv " #<---change this
OUTPUT_FILE = "outputfile.csv" #<---change this

# -----------------------------

def bulk_move(destination, in_file, out_file):
    url = CFG.API_BASE_URL + "/investigate"
    
    # Read postfix IDs
    with open(in_file, "r") as f:
        postfix_ids = [line.strip() for line in f if line.strip()]

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


