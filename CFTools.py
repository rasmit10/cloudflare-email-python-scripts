#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse

import CFFullSearch as CFSearch
import CF_BlockSender as CFBlock
import CFScriptConfig as CFG

# ---------------------------
# CLI run based off passed arugments
# ---------------------------
def args_run():
    #run search
    if(args.search):
        # search off message ID
        if args.id != None:
            print(args.id)
            items, meta = CFSearch.fetch_by_message_id(args.id, per_page=CFG.PER_PAGE, preserve_duplicates=True)
            print(f"[done] message-id fetch collected {len(items)} items; meta={meta}")
        
        # search off sender or domain
        else:
            end_dt = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
            start_dt = (end_dt - timedelta(days=int(args.days))).replace(tzinfo=timezone.utc)
            start_iso = CFSearch._iso(start_dt)
            end_iso = CFSearch._iso(end_dt)

            print(f"[search] start={start_iso} end={end_iso} per_page={CFG.PER_PAGE}")
            items, meta = CFSearch.fetch_all_by_time_divide_and_conquer(start_iso, end_iso, subject=args.subject, sender=args.sender, domain=args.domain, query=args.query, per_page=CFG.PER_PAGE)
            print(f"[done] collected {len(items)} items; meta={meta}")
        
        # items returned by search
        if len(items) > 0:
            # parse output path cf_investigate_timestamp.csv
            default_csv = Path.cwd() / f"cf_investigate_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.csv"
            if not args.out:
                out_csv = str(default_csv)
            else:
                p = Path(args.out).expanduser()
                if not p.suffix:
                    p = p.with_suffix(".csv")
                out_csv = str(p)

            #write output
            ok, written = CFSearch.export_csv_and_validate(out_csv, items)
            if ok:
                print(f"\n[success] CSV exported to {out_csv} with {written} rows (matches collected count).")
            else:
                print(f"\n[warning] CSV exported to {out_csv} with {written} rows (MAY NOT MATCH collected count {len(items)}). See debug/ for diagnostics.")
        else:
            print("\n[success] Search returned 0 results. No CSV output to write.")
    
    # add entry to block list
    elif(args.block):
        if not args.comment:
            print("\n[error] note is required when adding entry to block list")
            return
        if args.sender:
            res = CFBlock.add_entry_to_blocklist(args.comment, sender=args.sender)
        elif args.domain:
            res = CFBlock.add_entry_to_blocklist(args.comment, domain=args.domain)
        else:
            print("\n[error] sender or domain is required when adding entry to block list")
            return
        print(f"\n[success] added {res['pattern']} to block list with comment {res['comments']}.")

if __name__ == "__main__":
    #parse for command line arguments
    parser = argparse.ArgumentParser(description="Uses the Cloudflare API to search for messages and save the results as a CSV file. Use the following arguments to specify search peramaters or run without arguments for an interactive prompt.")
    parser.add_argument('-s', '--search', action='store_true', dest='search', help='Search for emails based on the arguments you provided. Use the other flags to provide search perameters.')
    parser.add_argument("-b", '--block', action="store_true", dest='block', help="Add a sender to the cloudflare block list. Use the sender or domain flag to specify what to block and the note flag to specify the block note.")
    parser.add_argument('--id', action='store', dest='id', default=None, help='The message ID of the email in double quotes ("<id>")')
    parser.add_argument('--days', action='store', dest='days', default=30, help='The number of days to search back. Defaults to 30 days')
    parser.add_argument('--subject', action='store', dest='subject', default=None, help='The subject of the email.')
    parser.add_argument('--sender', action='store', dest='sender', default=None, help='The sender of the email.')
    parser.add_argument('--domain', action='store', dest='domain', default=None, help='The sender domain.')
    parser.add_argument('--query', action='store', dest='query', default=None, help='A more advanced query to search for, analogous to the keyword search in the GUI')
    parser.add_argument('--out', action='store', dest='out', default=None, help='The output filepath for the query results.')
    parser.add_argument('-c', '--comment', action='store', dest='comment', help='The comment to add to the block list entry. Typical format: YYYY/MM/DD - SIR#')
    args = parser.parse_args()

    if args.search or args.block:
        args_run()
    else:
        print("Please use either a search or block argument. Run with -h for help.")
        