# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 07:59:50 2025

@author: rasmit10
"""
import os
import requests
from dotenv import load_dotenv
from pathlib import Path

import CFScriptConfig as CFG

# -----------------------------------------------------------
# MOVE MESSAGE
# -----------------------------------------------------------

def move_message(postfix_id: str, destination: str):
    """Move a message using Cloudflare Email Security Investigate API."""

    VALID_DESTINATIONS = {
        "Inbox",
        "JunkEmail",
        "DeletedItems",
        "RecoverableItemsDeletions",
        "RecoverableItemsPurges",
    }

    if destination not in VALID_DESTINATIONS:
        raise ValueError(f"Invalid destination. Must be one of: {sorted(VALID_DESTINATIONS)}")

    url = CFG.API_BASE_URL + f"investigate/{postfix_id}/move"
    body = {"destination": destination}

    headers = {
        "X-Auth-Email": CFG.AUTH_EMAIL,
        "X-Auth-Key": CFG.AUTH_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=CFG.TIMEOUT)
    except requests.RequestException as e:
        return {"success": False, "error": f"Request failed: {e}"}

    # Handle API-level errors
    if response.status_code not in (200, 201):
        return {"success": False, "error": response.text}

    # Cloudflare returns result as dict or list
    data = response.json()
    result = data.get("result", data)

    # Normalize list → dict
    if isinstance(result, list):
        if len(result) > 0 and isinstance(result[0], dict):
            result = result[0]
        else:
            result = {}

    print("\n✔ Message moved successfully!")
    print("Destination: ", result.get("destination"))
    print("Items moved: ", result.get("item_count"))
    print("Completed:   ", result.get("completed_timestamp"), "\n")

    return result


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

if __name__ == "__main__":
    postfix_id = "{enterpostfixid}"
    destination = "{enterdestination}"

    # Call the function
    move_message(postfix_id, destination)
