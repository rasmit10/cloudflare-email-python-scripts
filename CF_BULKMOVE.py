# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 09:00:35 2025

Cloudflare BULK MOVE

@author: rasmit10
"""

import requests
import csv
import json

import CFSearchConfig as CFG

url = CFG.API_BASE_URL + "/investigate"

# -----------------------------
# CONFIG — EDIT THESE
# -----------------------------
DESTINATION = "RecoverableItemsDeletions"     # Options["Inbox", "JunkEmail", "DeletedItems", "RecoverableItemsDeletions", "RecoverableItemsPurges"]

INPUT_FILE = r"inputfile.csv " #<---change this
OUTPUT_FILE = "outputfile.csv" #<---change this

# -----------------------------


# Read postfix IDs
with open(INPUT_FILE, "r") as f:
    postfix_ids = [line.strip() for line in f if line.strip()]

print(f"Loaded {len(postfix_ids)} postfix IDs")


# Prepare CSV output
fieldnames = ["postfix_id", "http_status", "success", "error", "raw_response"]
with open(OUTPUT_FILE, "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    # Process each ID one-by-one
    for postfix_id in postfix_ids:
        print(f"Moving {postfix_id} → {DESTINATION} ... ", end="")

        url = f"{url}/{postfix_id}/move"
        body = {"destination": DESTINATION}

        headers = {
            "X-Auth-Email": CFG.AUTH_EMAIL,
            "X-Auth-Key": CFG.AUTH_KEY,
            "Content-Type": "application/json",
        }

        response = requests.post(url, headers=headers, json=body)

        try:
            data = response.json()
        except:
            data = {"error": "Non-JSON response", "raw": response.text}

        success = data.get("success", False)
        error_msg = None

        # Cloudflare may return errors inside 'errors'
        if isinstance(data, dict) and "errors" in data and data["errors"]:
            error_msg = json.dumps(data["errors"])

        print("OK" if success else "FAILED")

        # Write row
        writer.writerow({
            "postfix_id": postfix_id,
            "http_status": response.status_code,
            "success": success,
            "error": error_msg,
            "raw_response": json.dumps(data)
        })

print(f"\nDone! Results written to {OUTPUT_FILE}")


