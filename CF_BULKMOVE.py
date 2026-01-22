# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 09:00:35 2025

Cloudflare BULK MOVE

"""

import csv
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

def bulk_move(destination, in_file, out_file):
    url = CFG.API_BASE_URL + "/investigate/move"
    
    # Read postfix IDs
    postfix_ids = read_postfix_id_csv(in_file)

    print(f"Loaded {len(postfix_ids)} postfix IDs")

    # ---------------------------
    # Batch Purge Processing
    # ---------------------------
    batch_size = 100 
    batch_count = 0
    failed_batches = []   # Track failed batches for retry attempts
    items = []

    # Iterate through postfix IDs in chunks of batch_size
    for i in range(0, len(postfix_ids), batch_size):
        batch_count += 1
        batch = postfix_ids[i:i + batch_size]

        print(f"Moving batch {batch_count} to {destination}...")

        body = {
        "destination": destination,
        "postfix_ids": batch
        }

        # Send purge request
        response = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)

        if response:
            print(f"Batch {batch_count} moved!")
        if "result" in response.json():
            for item in response.json()["result"]:
                items.append(item) # store purge results per message
        else:
            failed_batches.append(batch_count - 1)  # store failed batch index
            print(f"Problem with batch {batch_count} - {response.text}")

    # ---------------------------
    # Retry Logic For Failed Batches
    # ---------------------------

    if len(failed_batches) > 0:
        print("\nRetrying failed batches...")

        for failure in failed_batches:
            print(f"Retrying batch {failure + 1}")

        # Extract the same batch again
        retry_batch = postfix_ids[failure * batch_size : (failure + 1) * batch_size]

        # Retry each postfix_id individually
        for id in retry_batch:
            body = {
            "destination": destination,
            "postfix_ids": [id]
            }

            result, response = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)

            if result:
                print(f"Retry postfix_id {id} moved!")
            if "result" in response.json():
                for item in response.json()["result"]:
                    items.append(item)
            else:
                print(f"Problem with postfix_id {item} - {response.text}")

    # If there were "successful" purges, record the results
    if len(items) > 0:
        print(f"Saving move results to {out_file}")

        fieldnames = [
        "completed_timestamp", "success", "message_id", 
        "recipient", "operation", "status", "destination"
        ]

        # Write purge results to CSV
        with open(out_file, "w", newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(items)
            print(f"Results saved to {out_file}")

    else:
        print("No successful moves happened!")
        

if __name__ == "__main__":
    bulk_move(DESTINATION, INPUT_FILE, OUTPUT_FILE)


