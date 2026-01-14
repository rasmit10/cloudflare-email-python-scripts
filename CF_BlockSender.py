# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 12:59:34 2025

Cloudflare Block Sender

@author: rasmit10
"""


# -*- coding: utf-8 -*-
"""
Simple script to block a sender, domain, or IP in Cloudflare Email Security.
Prompts user for pattern, pattern_type, and case number.
"""

import sys
import requests
from datetime import datetime

import CFScriptConfig as CFG

SETTINGS_BASE = CFG.API_BASE_URL + "/settings"

def block_sender(pattern, pattern_type, case_number):
    # Cloudflare handles regex internally — NO regex flag needed
        is_regex = False

        comment = f"{datetime.utcnow().strftime('%Y/%m/%d')} - {case_number}"

        body = {
            "pattern": pattern,
            "pattern_type": pattern_type,
            "is_regex": is_regex,
            "comments": comment
        }

        # -----------------------------------------------------------
        # SEND API REQUEST
        # -----------------------------------------------------------

        url = f"{SETTINGS_BASE}/block_senders"
        resp = CFG.session.post(url, json=body, timeout=10)


        try:
            data = resp.json()
        except Exception:
            data = {}

        result = data.get("result")
        return result

       


if __name__ == "__main__":
    # -----------------------------------------------------------
    # USER INPUTS
    # -----------------------------------------------------------

    pattern = input("Enter sender / domain / IP to block: ").strip()
    if not pattern:
        print("No pattern entered. Exiting.")
        sys.exit(1)

    case_number = input("Enter case number: ").strip()
    if not case_number:
        print("No case number entered. Exiting.")
        sys.exit(1)

    print("\nChoose pattern type:")
    print("  1 = EMAIL   (example: user@example.com)")
    print("  2 = DOMAIN  (example: badsite.com)")
    print("  3 = IP      (example: 192.168.1.10)")
    print("  4 = UNKNOWN (rare — only if unsure)")

    ptype = input("Enter 1, 2, 3, or 4: ").strip()

    if ptype == "1":
        pattern_type = "EMAIL"
    elif ptype == "2":
        pattern_type = "DOMAIN"
    elif ptype == "3":
        pattern_type = "IP"
    elif ptype == "4":
        pattern_type = "UNKNOWN"
    else:
        print("Invalid choice. Defaulting to EMAIL.")
        pattern_type = "EMAIL"

    result= block_sender(pattern, ptype, case_number)

    # -----------------------------------------------------------
    # OUTPUT
    # -----------------------------------------------------------

    print("\n✅ Block created successfully!")
    print("------------------------------")
    print(f"Pattern     : {result.get('pattern')}")
    print(f"Type        : {result.get('pattern_type')}")
    print(f"Is Regex    : {result.get('is_regex')}")
    print(f"Comments    : {result.get('comments')}")
    print(f"Created ID  : {result.get('id')}")
    print("------------------------------")