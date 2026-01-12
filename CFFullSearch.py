101#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cf_investigate_fetch_csv_with_msgid_batch_v2.py

Updated: removed the prompt for delay between message-ID queries and added
graceful handling for missing input CSV files.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import time
import json
import csv
import os
import re
import uuid
import requests
from dotenv import load_dotenv

# ---------------------------
# CONFIG / TUNABLES
# ---------------------------
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID")
AUTH_EMAIL = os.getenv("CLOUDFLARE_EMAIL")
AUTH_KEY = os.getenv("CLOUDFLARE_API_KEY")

if not all((ACCOUNT_ID, AUTH_EMAIL, AUTH_KEY)):
    raise EnvironmentError("Missing CF_ACCOUNT_ID or CLOUDFLARE_EMAIL or CLOUDFLARE_API_KEY in environment or .env")

API_BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/email-security/investigate"

API_MAX_PER_PAGE = 1000
PER_PAGE = 1000      # Cloudflare limit
TIMEOUT = 90
MAX_RETRIES = 5
SLEEP_BETWEEN_REQUESTS = 0.05
RATE_LIMIT_SLEEP = 1.0

# Safety caps
MAX_TOTAL_REQUESTS = 200000
MAX_RECURSION_DEPTH = 40

# Chunking settings
MIN_CHUNK_SECONDS = 0.001   # 1 ms
MICRO_SUBSLICES = 10

# Debug & checkpoint folder
DEBUG_DIR = Path.cwd() / "debug"
DEBUG_DIR.mkdir(exist_ok=True)
MSGID_PROGRESS = DEBUG_DIR / "msgid_progress.json"

# Default delay between each message-id query (no prompt)
DELAY_BETWEEN_IDS = 0.2

# HTTP session
session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "X-Auth-Email": AUTH_EMAIL,
    "X-Auth-Key": AUTH_KEY
})

# ---------------------------
# Helpers (unchanged / reused)
# ---------------------------
def _iso(dt: datetime):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def _parse_iso_to_dt_or_none(s: str):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def _get_record_id(rec):
    if not rec:
        return None
    if isinstance(rec, dict):
        for k in ("postfix_id", "message_id", "id", "msg_id", "messageId"):
            v = rec.get(k)
            if v:
                return str(v)
    else:
        for k in ("postfix_id", "message_id", "id"):
            v = getattr(rec, k, None)
            if v:
                return str(v)
    try:
        return json.dumps(rec, sort_keys=True, default=str)[:400]
    except Exception:
        return str(rec)[:400]

def _save_debug_response(resp, params, url, note=None):
    try:
        fname = DEBUG_DIR / f"resp_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}.json"
        try:
            body = resp.json() if resp is not None else None
        except Exception:
            try:
                body = resp.text
            except Exception:
                body = "<unreadable>"
        obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request": {"url": url, "params": params},
            "status": resp.status_code if resp is not None else None,
            "headers": dict(resp.headers) if resp is not None else None,
            "body": body,
            "note": note,
        }
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
        return str(fname)
    except Exception as e:
        print("[debug] failed to save resp:", e)
        return None

def _extract_cursor_from_next(next_val):
    if not next_val:
        return None
    if isinstance(next_val, str) and (next_val.startswith("http://") or next_val.startswith("https://")):
        try:
            parsed = requests.utils.urlparse(next_val)
            qs = requests.utils.parse_qs(parsed.query)
            for k in ("cursor", "next", "after"):
                if k in qs and qs[k]:
                    return qs[k][0]
            return next_val
        except Exception:
            return next_val
    return next_val

# ---------------------------
# Single page fetch with retries + debug (shared)
# ---------------------------
def _fetch_page(start_iso=None, end_iso=None, subject=None, sender=None, domain=None, query=None, per_page=PER_PAGE):
    params = {"per_page": per_page, "detections_only": "false"}
    if start_iso:
        params["start"] = start_iso
    if end_iso:
        params["end"] = end_iso

    if query:
        params["query"] = query
    else:
        if subject:
            params["subject"] = subject
        if sender:
            params["sender"] = sender
        if domain:
            params["domain"] = domain

    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(API_BASE_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as e:
            last_exc = e
            time.sleep((2 ** attempt) * 0.5)
            continue

        _save_debug_response(resp, params, API_BASE_URL, note=f"attempt_{attempt}")

        if resp.status_code == 200:
            try:
                data = resp.json()
            except Exception:
                data = {}
            page_results = data.get("result") or []
            if isinstance(page_results, dict):
                for k in ("items", "results", "data"):
                    if k in page_results:
                        page_results = page_results[k]
                        break
            if page_results is None:
                page_results = []
            ri = data.get("result_info") or {}
            return page_results, len(page_results), ri
        if resp.status_code in (429, 500, 502, 503, 504):
            time.sleep((2 ** attempt) * 0.5 + RATE_LIMIT_SLEEP)
            last_exc = Exception(f"Transient HTTP {resp.status_code}")
            continue
        raise Exception(f"API error {resp.status_code}: {resp.text}")
    raise last_exc if last_exc else Exception("Unknown request failure")

# ---------------------------
# Message-ID fetch (pages through server results) - reused
# ---------------------------
def fetch_by_message_id(message_id, per_page=PER_PAGE, preserve_duplicates=True):
    if not message_id:
        return [], {"requests_made": 0, "completed": True, "reason": "no_message_id"}

    collected = []
    requests_made = 0
    cursor = None
    max_iters = 10000

    for it in range(max_iters):
        params_query = {
            "query": message_id,
            "per_page": per_page,
            "detections_only": "false",
            }
        if cursor:
            params_query["cursor"] = cursor
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = session.get(API_BASE_URL, params=params_query, timeout=TIMEOUT)
            except requests.RequestException as e:
                last_exc = e
                time.sleep((2 ** attempt) * 0.5)
                continue
            _save_debug_response(resp, params_query, API_BASE_URL, note=f"msgid_attempt_{attempt}")
            if resp.status_code == 200:
                break
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep((2 ** attempt) * 0.5 + RATE_LIMIT_SLEEP)
                last_exc = Exception(f"Transient HTTP {resp.status_code}")
                continue
            raise Exception(f"API error {resp.status_code}: {resp.text}")
        if resp is None:
            raise last_exc or Exception("No response")
        requests_made += 1

        try:
            data = resp.json()
        except Exception:
            data = {}
        page = data.get("result") or []
        if isinstance(page, dict):
            for k in ("items", "results", "data"):
                if k in page:
                    page = page[k]
                    break
        if page is None:
            page = []

        for r in page:
            collected.append(r)

        ri = data.get("result_info") or {}
        next_val = ri.get("next") or data.get("next") or ri.get("next_cursor") or data.get("next_cursor") or None
        if not next_val:
            link_header = resp.headers.get("Link") or resp.headers.get("link")
            if link_header:
                m = re.findall(r'<([^>]+)>\s*;\s*rel="?([^",]+)"?', link_header)
                for url, rel in m:
                    if rel == "next":
                        next_val = url
                        break

        next_cursor = _extract_cursor_from_next(next_val)
        if next_cursor:
            cursor = next_cursor
            time.sleep(SLEEP_BETWEEN_REQUESTS)
            continue
        break

    meta = {"requests_made": requests_made, "completed": True, "reason": "done"}
    return collected, meta

# ---------------------------
# Deterministic divide-and-conquer fetcher (unchanged)
# ---------------------------
def fetch_all_by_time_divide_and_conquer(start_iso, end_iso, subject=None, sender=None, domain=None, query=None, per_page=PER_PAGE):
    start_dt = _parse_iso_to_dt_or_none(start_iso)
    end_dt = _parse_iso_to_dt_or_none(end_iso)
    if not start_dt or not end_dt:
        raise ValueError("start_iso/end_iso must be valid ISO strings")

    collected = []
    seen_ids = set()
    requests_made = 0
    aborted = False

    def _recurse(s_dt: datetime, e_dt: datetime, depth=0):
        nonlocal requests_made, aborted
        if aborted:
            return
        if requests_made >= MAX_TOTAL_REQUESTS:
            aborted = True
            print("[abort] reached MAX_TOTAL_REQUESTS")
            return
        if s_dt >= e_dt:
            return

        chunk_seconds = (e_dt - s_dt).total_seconds()
        if depth > MAX_RECURSION_DEPTH:
            print(f"[warn] max recursion depth ({MAX_RECURSION_DEPTH}) reached; fetching once: {s_dt} -> {e_dt}")
            try:
                page, plen, ri = _fetch_page(_iso(s_dt), _iso(e_dt), subject=subject, sender=sender, domain=domain, query=query, per_page=per_page)
                requests_made += 1
            except Exception as ex:
                print("[error] request failed at max depth:", ex)
                aborted = True
                return
            for r in page:
                rid = _get_record_id(r)
                if rid not in seen_ids:
                    seen_ids.add(rid)
                    collected.append(r)
            return

        try:
            page, plen, ri = _fetch_page(_iso(s_dt), _iso(e_dt), subject=subject, sender=sender, domain=domain, query=query, per_page=per_page)
            requests_made += 1
        except Exception as ex:
            print("[error] request failed:", ex)
            aborted = True
            return

        print(f"[chunk depth={depth}] {s_dt.isoformat()} -> {e_dt.isoformat()} : returned {plen} items (requests={requests_made})")

        for r in page:
            rid = _get_record_id(r)
            if rid not in seen_ids:
                seen_ids.add(rid)
                collected.append(r)

        if plen < per_page:
            return

        if chunk_seconds <= MIN_CHUNK_SECONDS:
            delta = (e_dt - s_dt) / MICRO_SUBSLICES
            if delta.total_seconds() <= 0:
                print("[warn] cannot split tiny chunk further; accepting current results from this chunk")
                return
            for i in range(MICRO_SUBSLICES):
                a = s_dt + delta * i
                b = s_dt + delta * (i + 1)
                _recurse(a, b, depth + 1)
                if aborted:
                    return
            return

        mid = s_dt + (e_dt - s_dt) / 2
        _recurse(s_dt, mid, depth + 1)
        if aborted:
            return
        _recurse(mid, e_dt, depth + 1)

    _recurse(start_dt, end_dt, depth=0)

    meta = {"requests_made": requests_made, "completed": not aborted, "reason": "done" if not aborted else "aborted"}
    return collected, meta

# ---------------------------
# Flatten + CSV export (unchanged)
# ---------------------------
def flatten_record(rec, parent_key="", out=None):
    if out is None:
        out = {}

    if isinstance(rec, dict):
        for k, v in rec.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            flatten_record(v, new_key, out)

    elif isinstance(rec, list):
        parts = []
        for x in rec:
            if isinstance(x, (dict, list)):
                parts.append(json.dumps(x, ensure_ascii=False))
            else:
                parts.append(str(x))
        out[parent_key] = ";".join(parts)

    else:
        out[parent_key] = "" if rec is None else str(rec)

    return out

def export_csv_and_validate(path, items):
    p = Path(path)
    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)

    flat_rows = []
    all_keys = set()

    for rec in items:
        flat = flatten_record(rec)
        flat_rows.append(flat)
        all_keys.update(flat.keys())

    fieldnames = sorted(all_keys)

    written = 0
    try:
        with open(p, "w", newline="", encoding="utf-8") as cf:
            writer = csv.DictWriter(cf, fieldnames=fieldnames)
            writer.writeheader()
            for flat in flat_rows:
                row = {k: flat.get(k, "") for k in fieldnames}
                writer.writerow(row)
                written += 1
    except Exception as e:
        print("[error] Failed to write CSV:", e)
        return False, 0

    if written != len(items):
        print(f"[error] mismatch: collected {len(items)} items but wrote {written} rows.")
        return False, written

    return True, written

# ---------------------------
# Read/Checkpoint helpers for Message ID CSV processing
# ---------------------------
def read_message_id_csv(path):
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
    for name in ("message_id", "message-id", "msgid", "msg_id", "id"):
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

def load_msgid_progress():
    if MSGID_PROGRESS.exists():
        try:
            return json.loads(MSGID_PROGRESS.read_text(encoding="utf-8"))
        except Exception:
            return {"done_ids": [], "index": 0}
    return {"done_ids": [], "index": 0}

def save_msgid_progress(progress_obj):
    try:
        MSGID_PROGRESS.write_text(json.dumps(progress_obj, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        print("[debug] failed to write progress:", e)

def process_message_id_file(in_csv_path, out_csv_path, delay_between_ids=DELAY_BETWEEN_IDS):
    # graceful handling of missing file
    in_path = Path(in_csv_path)
    if not in_path.exists():
        print(f"[error] input file not found: {in_path}")
        return False, 0

    ids = read_message_id_csv(in_csv_path)
    if not ids:
        print("[error] No message IDs found in input CSV.")
        return False, 0

    progress = load_msgid_progress()
    done_ids = set(progress.get("done_ids", []))
    start_index = progress.get("index", 0)
    if start_index < len(ids) and ids[start_index] in done_ids:
        for i, mid in enumerate(ids):
            if mid not in done_ids:
                start_index = i
                break

    collected_all = []
    requests_total = 0
    print(f"[batch] total ids in file: {len(ids)} starting at index {start_index}")

    for idx in range(start_index, len(ids)):
        mid = ids[idx]
        print(f"[batch] ({idx+1}/{len(ids)}) fetching message id: {mid}")
        try:
            page_items, meta = fetch_by_message_id(mid, per_page=PER_PAGE, preserve_duplicates=True)
        except Exception as e:
            print(f"[error] failed to fetch {mid}: {e}")
            progress["index"] = idx
            progress["done_ids"] = list(done_ids)
            save_msgid_progress(progress)
            return False, len(collected_all)
        for r in page_items:
            collected_all.append(r)
        requests_total += meta.get("requests_made", 0) if isinstance(meta, dict) else 1
        done_ids.add(mid)
        progress["index"] = idx + 1
        progress["done_ids"] = list(done_ids)
        save_msgid_progress(progress)
        time.sleep(delay_between_ids)

    print(f"[batch done] fetched total records across IDs: {len(collected_all)} requests_total={requests_total}")
    ok, written = export_csv_and_validate(out_csv_path, collected_all)
    if ok:
        try:
            MSGID_PROGRESS.unlink()
        except Exception:
            pass
        print(f"[success] batch CSV exported to {out_csv_path} with {written} rows.")
        return True, written
    else:
        print(f"[warning] batch CSV exported to {out_csv_path} with {written} rows (may not match).")
        return False, written

# ---------------------------
# CLI prompt and run (menu + CSV-of-msgid option) - delay prompt removed
# ---------------------------
def prompt_run():
    print("Cloudflare Email Investigate - CSV-only fetcher with Message ID batch support")
    print("Options:")
    print(" 1) Time-window / domain / subject search (existing flow)")
    print(" 2) Single Message ID lookup (existing flow)")
    print(" 3) Process CSV file of Message IDs (new)")

    choice = input("Choose 1 / 2 / 3 (default 1): ").strip() or "1"
    if choice == "2":
        message_id = input("Message ID (exact) : ").strip() or None
        if not message_id:
            print("No Message ID provided.")
            return
        items, meta = fetch_by_message_id(message_id, per_page=PER_PAGE, preserve_duplicates=True)
        print(f"[done] message-id fetch collected {len(items)} items; meta={meta}")
    elif choice == "3":
        in_csv = input("Path to CSV file containing Message IDs: ").strip()
        if not in_csv:
            print("[error] No input file path provided.")
            return
        default_out = Path.cwd() / f"cf_investigate_msgid_batch_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
        out_csv_input = input(f"Export CSV path (press Enter to use default {default_out}): ").strip()
        if not out_csv_input:
            out_csv = str(default_out)
        else:
            p = Path(out_csv_input).expanduser()
            if not p.suffix:
                p = p.with_suffix(".csv")
            out_csv = str(p)

        # use default delay (no prompt per your request)
        delay_between = DELAY_BETWEEN_IDS
        ok, written = process_message_id_file(in_csv, out_csv, delay_between_ids=delay_between)
        return
    else:
        subject = input("Subject (leave blank to skip): ").strip() or None
        sender = input("Sender (email, leave blank to skip): ").strip() or None
        domain = input("Domain (sender domain, leave blank to skip): ").strip() or None
        query = input("Broad query (space-separated terms, leave blank to skip): ").strip() or None
        try:
            days_back_raw = input("Days back (integer, default 1): ").strip()
            days_back = int(days_back_raw) if days_back_raw else 1
        except Exception:
            days_back = 1

        end_dt = datetime.utcnow().replace(tzinfo=timezone.utc)
        start_dt = (end_dt - timedelta(days=days_back)).replace(tzinfo=timezone.utc)
        start_iso = _iso(start_dt)
        end_iso = _iso(end_dt)

        print(f"[search] start={start_iso} end={end_iso} per_page={PER_PAGE}")
        items, meta = fetch_all_by_time_divide_and_conquer(start_iso, end_iso, subject=subject, sender=sender, domain=domain, query=query, per_page=PER_PAGE)
        print(f"[done] collected {len(items)} items; meta={meta}")

    default_csv = Path.cwd() / f"cf_investigate_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    out_csv_input = input(f"Export CSV path (press Enter to use default {default_csv}): ").strip()
    if not out_csv_input:
        out_csv = str(default_csv)
    else:
        p = Path(out_csv_input).expanduser()
        if not p.suffix:
            p = p.with_suffix(".csv")
        out_csv = str(p)

    ok, written = export_csv_and_validate(out_csv, items)
    if ok:
        print(f"[success] CSV exported to {out_csv} with {written} rows (matches collected count).")
    else:
        print(f"[warning] CSV exported to {out_csv} with {written} rows (MAY NOT MATCH collected count {len(items)}). See debug/ for diagnostics.")

if __name__ == "__main__":
    prompt_run()
