
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cloudflare Domain Check
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from typing import List, Dict, Any

# ---------------------------
# CONFIG — edit this (IDE)
# ---------------------------
SEARCH_DOMAIN = "azte.com"   # set to domain you want to check (e.g. "example.com")
PER_PAGE = 100

# ---------------------------
# LOAD ENVIRONMENT
# ---------------------------
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not all([ACCOUNT_ID, AUTH_EMAIL, AUTH_KEY]):
    raise EnvironmentError("Missing CF_ACCOUNT_ID or CLOUDFLARE_EMAIL or CLOUDFLARE_API_KEY in .env")

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/settings/domains"
HEADERS = {
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY,
    "Accept": "application/json",
}

# ---------------------------
# Fetch all domains (paged)
# ---------------------------
def fetch_all_domains(per_page: int = PER_PAGE) -> List[Dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)
    page = 1
    all_items: List[Dict[str, Any]] = []

    while True:
        resp = session.get(BASE_URL, params={"per_page": per_page, "page": page}, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("result") or []
        if not isinstance(items, list):
            items = list(items) if items else []
        if not items:
            break
        all_items.extend(items)
        if len(items) < per_page:
            break
        page += 1

    return all_items

# ---------------------------
# Matching helpers
# ---------------------------
def _is_subdomain_of(candidate: str, parent: str) -> bool:
    """
    Return True if candidate is exactly parent or is a subdomain of parent.
    Example: candidate='foo.sub.example.com', parent='example.com' -> True
    """
    c = candidate.strip().lower()
    p = parent.strip().lower()
    if c == p:
        return True
    return c.endswith("." + p)

def domain_matches_config(search_domain: str, config_domain_entry: Dict[str, Any]) -> bool:
    """
    Returns True if the search_domain matches the config entry's 'domain' (exact or subdomain).
    """
    cfg = (config_domain_entry.get("domain") or "").strip().lower()
    if not cfg:
        return False
    return _is_subdomain_of(search_domain, cfg) or _is_subdomain_of(cfg, search_domain)

# ---------------------------
# Main (IDE)
# ---------------------------
def main():
    if not SEARCH_DOMAIN or not SEARCH_DOMAIN.strip():
        raise ValueError("Set SEARCH_DOMAIN at top of script to the domain you want to check (e.g. 'example.com').")

    sd = SEARCH_DOMAIN.strip().lower()
    print(f"[info] fetching configured domains for account {ACCOUNT_ID} ...")
    try:
        domains = fetch_all_domains()
    except Exception as e:
        print("[error] failed to fetch domains:", e)
        return

    print(f"[info] fetched {len(domains)} domain entries")
    matches = []
    for d in domains:
        try:
            if domain_matches_config(sd, d):
                matches.append(d)
        except Exception:
            continue

    if not matches:
        print(f"[result] {sd} is NOT configured in Email Security domains.")
        return

    print(f"[result] {sd} matched {len(matches)} configured domain entry(ies):")
    for i, m in enumerate(matches, start=1):
        print(f"{i}. id={m.get('id')} domain={m.get('domain')}")
        print(f"    allowed_delivery_modes: {m.get('allowed_delivery_modes')}")
        print(f"    active_delivery_mode: {m.get('transport') or m.get('active_delivery_mode')}")
        print(f"    inbox_provider: {m.get('inbox_provider')}")
        print(f"    dmarc_status: {m.get('dmarc_status')}")
        print(f"    spf_status: {m.get('spf_status')}")
        print(f"    drop_dispositions: {m.get('drop_dispositions')}")
        print()

if __name__ == "__main__":
    main()
