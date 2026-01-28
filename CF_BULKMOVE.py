# -*- coding: utf-8 -*-
"""
Created on Thu Dec  4 09:00:35 2025

Cloudflare BULK MOVE

"""

import csv
import time
from pathlib import Path
import CFScriptConfig as CFG


# -----------------------------
# CONFIG — EDIT THESE
# -----------------------------
DESTINATION = "RecoverableItemsDeletions"     # Options["Inbox", "JunkEmail", "DeletedItems", "RecoverableItemsDeletions", "RecoverableItemsPurges"]

INPUT_FILE = r"inputfile.csv " #<---change this
OUTPUT_FILE = "outputfile.csv" #<---change this

# -----------------------------
def single_move(postfix_id, destination):
    
    url = f"{CFG.API_BASE_URL}/investigate/{postfix_id}/move"
    body = {"destination": destination}

    response = CFG.session.post(url, json=body, timeout=CFG.TIMEOUT)
    return response


def read_postfix_id_csv(path): # type: ignore
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

def _parse_json_response(response):
    """
    Safely parse JSON from a requests.Response.
    Returns (parsed_json or None, error_message or None).
    """
    # 204 No Content -> nothing to parse
    if response.status_code == 204:
        return None, None

    # Quick Content-Type check (may be missing or generic)
    ctype = response.headers.get("Content-Type", "")
    if "application/json" not in ctype and response.text.strip() == "":
        # empty body and not JSON
        return None, f"Empty response body (status {response.status_code})"
    try:
        return response.json(), None
    except ValueError as e:
        # Could not decode JSON; return text for diagnostics
        return None, f"JSON decode error: {e}; body: {response.text[:1000]}"

def bulk_move(destination, in_file, out_file):
    url = CFG.API_BASE_URL + "/investigate/move"
    postfix_ids = read_postfix_id_csv(in_file)

    print(f"Loaded {len(postfix_ids)} postfix IDs")

    batch_size = 100
    failed_batches = []   # store batch start indices for retries
    items = []

    for start in range(0, len(postfix_ids), batch_size):
        batch = postfix_ids[start:start + batch_size]
        batch_num = (start // batch_size) + 1
        print(f"Moving batch {batch_num} to {destination}...")

        body = {
            "destination": destination,
            "postfix_ids": batch
        }

        try:
            response = CFG.session.post(url, json=body)
        except Exception as e:
            print(f"HTTP request failed for batch {batch_num}: {e}")
            failed_batches.append(start)
            continue

        parsed, error = _parse_json_response(response)
        # Debug/log status and body when non-JSON or error
        if error:
            print(f"Batch {batch_num} - parse issue: {error}; status_code={response.status_code}")
            print(f"Response headers: {response.headers}")
            # treat this as failure unless status indicates success with no content
            if response.status_code not in (200, 201, 204):
                failed_batches.append(start)
                continue
        else:
            # parsed is either dict/list or None for 204
            if response.status_code in (200, 201, 204):
                print(f"Batch {batch_num} moved! status={response.status_code}")
            else:
                print(f"Batch {batch_num} returned status {response.status_code}")

        # If we have JSON and it contains "result", gather items
        result = None
        if parsed and isinstance(parsed, dict):
            result = parsed.get("result", None)

        if isinstance(result, list):
            items.extend(result)
        elif result is not None:
            # result exists but is not a list
            print(f"Batch {batch_num} result field is not a list: {type(result)}; content: {str(result)[:500]}")
        else:
            # No result found in parsed JSON (could be None because of 204 or empty body)
            if response.status_code not in (200, 201, 204):
                failed_batches.append(start)
                print(f"Problem with batch {batch_num} - {response.text[:1000]}")
            else:
                # success but no result payload — that's acceptable for some APIs
                print(f"Batch {batch_num} succeeded with no 'result' payload.")

        time.sleep(2)

    # Retry logic for failed_batches
    if failed_batches:
        print("\nRetrying failed batches...")
        for start in failed_batches:
            batch_num = (start // batch_size) + 1
            retry_batch = postfix_ids[start : start + batch_size]
            print(f"Retrying batch {batch_num} (size {len(retry_batch)})")

            # Retry each postfix_id individually
            for pid in retry_batch:
                try:
                    response = single_move(pid, destination)
                except Exception as e:
                    print(f"HTTP request failed for postfix_id {pid}: {e}")
                    continue

                parsed, error = _parse_json_response(response)
                if error:
                    print(f"Retry postfix_id {pid} - parse issue: {error}; status={response.status_code}")
                    # keep trying next id; don't crash
                    continue

                if response.status_code in (200, 201, 204):
                    print(f"Retry postfix_id {pid} moved! status={response.status_code}")

                # Safely extract result list if present
                result = None
                if parsed and isinstance(parsed, dict):
                    result = parsed.get("result", None)

                if isinstance(result, list):
                    for item in result:
                        items.append(item)
                elif result is not None:
                    print(f"Retry postfix_id {pid} result field unexpected type: {type(result)}; content: {str(result)[:500]}")
                time.sleep(2)

    # Summarize and write output if any items
    if items:
        num_successes = sum(1 for item in items if item.get('status') == 'OK')
        print(f"Successfully moved {num_successes}/{len(items)} messages.")
        print(f"Saving move results to {out_file}")

        fieldnames = [
            "completed_timestamp", "success", "message_id",
            "recipient", "operation", "status", "destination"
        ]

        with open(out_file, "w", newline='', encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(items)
            print(f"Results saved to {out_file}")
    else:
        print("No successful moves happened!")

if __name__ == "__main__":
    bulk_move(DESTINATION, INPUT_FILE, OUTPUT_FILE)
