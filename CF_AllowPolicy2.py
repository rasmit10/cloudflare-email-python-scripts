#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloudflare Allow Policy Search by Email and Domain
"""

import os
import re
from pathlib import Path
from dotenv import load_dotenv
import requests

# -----------------------------------------------------------
# CONFIG – CHANGE THESE ONLY
# -----------------------------------------------------------
SEARCH_EMAIL = None  # set to None to search by domain
SEARCH_DOMAIN = "universitydesigninstitute.ccsend.com"                # e.g. "example.com"

PER_PAGE = 100

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

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/settings/allow_policies"
HEADERS = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Accept": "application/json",
}

# -----------------------------------------------------------
# HELPERS
# -----------------------------------------------------------
def wildcard_to_regex(pattern: str):
    esc = re.escape(pattern)
    esc = esc.replace(r"\*", ".*")
    return re.compile(r"^" + esc + r"$", re.IGNORECASE)

def email_domain(email: str) -> str:
    return email.split("@", 1)[1].lower() if "@" in email else ""

# -----------------------------------------------------------
# FETCH ALL ALLOW POLICIES
# -----------------------------------------------------------
def fetch_allow_policies():
    policies = []
    page = 1
    session = requests.Session()
    session.headers.update(HEADERS)

    while True:
        r = session.get(BASE_URL, params={"page": page, "per_page": PER_PAGE}, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data.get("result", [])
        if not results:
            break
        policies.extend(results)
        if len(results) < PER_PAGE:
            break
        page += 1

    return policies

# -----------------------------------------------------------
# MATCHING LOGIC
# -----------------------------------------------------------
def matches_email(policy, email: str) -> bool:
    pattern = (policy.get("pattern") or "").strip()
    ptype = (policy.get("pattern_type") or "").upper()
    email = email.lower()

    if not pattern:
        return False

    if ptype == "EMAIL":
        return wildcard_to_regex(pattern).match(email) is not None if "*" in pattern else pattern.lower() == email

    if ptype == "DOMAIN":
        dom = email_domain(email)
        return dom == pattern.lower() or dom.endswith("." + pattern.lower())

    return wildcard_to_regex(pattern).match(email) is not None if "*" in pattern else pattern.lower() in email

def matches_domain(policy, domain: str) -> bool:
    pattern = (policy.get("pattern") or "").strip()
    ptype = (policy.get("pattern_type") or "").upper()
    domain = domain.lower()

    if not pattern:
        return False

    if ptype == "DOMAIN":
        return domain == pattern.lower() or domain.endswith("." + pattern.lower())

    if ptype == "EMAIL" and "@" in pattern:
        _, pdom = pattern.rsplit("@", 1)
        return domain == pdom.lower() or domain.endswith("." + pdom.lower())

    return wildcard_to_regex(pattern).match(domain) is not None if "*" in pattern else pattern.lower() in domain

# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------
def main():
    if SEARCH_EMAIL and SEARCH_DOMAIN:
        raise ValueError("Set only one of SEARCH_EMAIL or SEARCH_DOMAIN")

    print("[info] fetching allow policies...")
    policies = fetch_allow_policies()
    print(f"[info] fetched {len(policies)} allow policies")

    matches = []

    if SEARCH_EMAIL:
        print(f"[search] email: {SEARCH_EMAIL}")
        for p in policies:
            if matches_email(p, SEARCH_EMAIL):
                matches.append(p)
    elif SEARCH_DOMAIN:
        print(f"[search] domain: {SEARCH_DOMAIN}")
        for p in policies:
            if matches_domain(p, SEARCH_DOMAIN):
                matches.append(p)
    else:
        raise ValueError("You must set SEARCH_EMAIL or SEARCH_DOMAIN")

    if not matches:
        print("[result] NOT on allow list")
        return

    print(f"[result] FOUND {len(matches)} matching allow policy(ies):")
    for i, m in enumerate(matches, 1):
        print(
            f"{i}. id={m.get('id')} "
            f"type={m.get('pattern_type')} "
            f"pattern={m.get('pattern')} "
            f"trusted={m.get('is_trusted_sender')}"
        )

# -----------------------------------------------------------
if __name__ == "__main__":
    main()
