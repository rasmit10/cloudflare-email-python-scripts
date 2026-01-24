#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse

import CFFullSearch as CFSearch
import CF_BlockSender as CFBlock
import CFScriptConfig as CFG
import CF_RECLASS as CFReclass
import CF_BULKMOVE as CFBulkMove

# ---------------------------
# Search for emails using arguments
# ---------------------------
def arg_search(args):
    if not any((args.sender, args.id, args.subject, args.domain, args.query, args.recipient)):
        print("[error] no search criteria specified. Run \'CFTools.py search -h\' for help. ")
        return
    # search off message ID
    if args.id != None:
        print(args.id)
        items, meta = CFSearch.fetch_by_message_id(args.id, per_page=CFG.PER_PAGE, preserve_duplicates=True)
        print(f"[done] message-id fetch collected {len(items)} items; meta={meta}")
    
    # search off sender, recipient, or domain
    else:
        end_dt = datetime.now(timezone.utc).replace(tzinfo=timezone.utc)
        start_dt = (end_dt - timedelta(days=int(args.days))).replace(tzinfo=timezone.utc)
        start_iso = CFSearch._iso(start_dt)
        end_iso = CFSearch._iso(end_dt)

        print(f"[search] start={start_iso} end={end_iso} per_page={CFG.PER_PAGE}")
        items, meta = CFSearch.fetch_all_by_time_divide_and_conquer(start_iso, end_iso, subject=args.subject, sender=args.sender, recipient=args.recipient, domain=args.domain, query=args.query, per_page=CFG.PER_PAGE)
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
            return
        else:
            print(f"\n[warning] CSV exported to {out_csv} with {written} rows (MAY NOT MATCH collected count {len(items)}). See debug/ for diagnostics.")
            return
    else:
        print("\n[success] Search returned 0 results. No CSV output to write.")
        return

# ---------------------------
# Add an entry to the block list using arguments
# ---------------------------
def arg_block(args):
    if not any((args.sender, args.domain)):
        print("[error] Sender or domain is required to add an entry to the block list. Run \'CFTools.py block -h\' for help.")
        return

    res = {}
    if args.sender:
        res = CFBlock.block_sender(args.sender, "EMAIL", args.case_number)
    elif args.domain:
        res = CFBlock.block_sender(args.domain, "DOMAIN", args.case_number)

    
    print(f"\n[success] added {res['pattern']} to block list with comment {res['comments']}.")
    return

# ---------------------------
# Submit a reclassification using arguments
# ---------------------------
def arg_reclassify(args):
    #reclassify a message
    if(not args.disposition):
        print("\n[error] postifx and disposition are required to reclassify a message. Run \'CFTools.py reclassify -h\' for help.")
        return
    if not any((args.postfix, args.input_file)):
        print("\n[error] either a postfix ID or input file is required. Run \'CFTools.py reclassify -h\' for help.")
        return
    
    if args.postfix:
        CFReclass.reclassify_message(args.postfix, args.disposition.upper())
    elif args.input_file:
        CFReclass.bulk_reclassify(args.input_file, args.number_of_successes, args.disposition)
    
    

def arg_move(args):
    if not any((args.postfix, args.input_file)):
        print("[error] either a postifx id or input csv is required.")
        return
    
    if args.input_file:
        CFBulkMove.bulk_move(args.destination, args.input_file, args.output_file)
    elif args.postfix:
        response = CFBulkMove.single_move(args.postfix, args.destination)
        if response.status_code == 200:
            print(f"[success] moved {args.postfix} to {args.destination}")
        else:
            print(f"[error] failed to move message with error {response.status_code}")



if __name__ == "__main__":
    #parse for command line arguments
    parser = argparse.ArgumentParser(description='Uses the Cloudflare API to search for messages and save the results as a CSV file. Use the subcommands below to specify an action.')
    subparser = parser.add_subparsers(dest = 'command')

    #define search parser and arguments
    search_parser = subparser.add_parser('search', help='Search Cloudflare for emails.')
    search_parser.set_defaults(func=arg_search)
    search_parser.add_argument('--id', action='store', dest='id', default=None, help='The message ID of the email in double quotes ("<id>")')
    search_parser.add_argument('--days', action='store', dest='days', default=30, help='The number of days to search back. Defaults to 30 days')
    search_parser.add_argument('--subject', action='store', dest='subject', default=None, help='The subject of the email.')
    search_parser.add_argument('-s', '--sender', action='store', dest='sender', default=None, help='The sender of the email.')
    search_parser.add_argument('-r', '--recipient', action='store', dest='recipient', default=None, help='The recipient of the email.')
    search_parser.add_argument('-d', '--domain', action='store', dest='domain', default=None, help='The sender domain.')
    search_parser.add_argument('--query', action='store', dest='query', default=None, help='A more advanced query to search for, analogous to the keyword search in the GUI')
    search_parser.add_argument('-o','--out', action='store', dest='out', default=None, help='The output filepath for the query results.')


    #define block parser and arguments
    block_parser = subparser.add_parser('block', help='Add a sender to the Cloudflare block list.')
    block_parser.set_defaults(func=arg_block)
    block_parser.add_argument('-s', '--sender', action='store', dest='sender', default=None, help='The sender to block.')
    block_parser.add_argument('-d', '--domain', action='store', dest='domain', default=None, help='The sender domain to block.')
    block_parser.add_argument('-c', '--case_number', action='store', dest='case_number', help='The case number of the SIR the sender is being blocked for. Used to generate the block list comment.', required=True)


    #define reclassify parser and arguments
    reclassify_parser = subparser.add_parser('reclassify', help='Submit a message to Cloudflare for reclassification.')
    reclassify_parser.set_defaults(func=arg_reclassify)
    reclassify_parser.add_argument('-p', "--postfix", action='store', dest='postfix', help='The postix ID of the message.')
    reclassify_parser.add_argument('-i', '--input_file', action='store', dest='input_file', help='The path to the input csv file. If used, submission attempts will be made until X successful submissions are made.')
    reclassify_parser.add_argument('-n', '--number_of_successes', action='store', dest='number_of_successes', default=2, help='The number of successful submissions required when bulk processing using an input file. Default: 2')
    reclassify_parser.add_argument('-d', '--disposition', action='store', dest='disposition', choices=['none', 'bulk', 'malicious', 'spam', 'spoof', 'suspicious'], help='The desired disposition of a message. Options: none | bulk | malicious | spam | spoof | suspicious', required=True)

    #define move parser and add arguments
    move_parser = subparser.add_parser('move', help='Move a list of messages to a different folder.')
    move_parser.set_defaults(func=arg_move)
    move_parser.add_argument('-d', '--destination', action='store', dest="destination", choices=["Inbox", "JunkEmail", "DeletedItems", "RecoverableItemsDeletions", "RecoverableItemsPurges"], help='The destination folder to move the messages to. Options: Inbox | JunkEmail | DeletedItems | RecoverableItemsDeletions | RecoverableItemsPurges', required=True)
    move_parser.add_argument('-i', '--input_file', action='store', dest='input_file', help='The path of the input CSV.')
    move_parser.add_argument('-o', '--output_file', action='store', dest='output_file', help="The file path to output the results csv to. Default is move_results.csv", default="move_results.csv")
    move_parser.add_argument('-p', '--postifx', action='store', dest='postfix', help='The postifx ID of a single email to move.')

    #parse arguments and run the correct function
    args = parser.parse_args()

    if args.command:
        args.func(args)
    else:
        print("[error] A subcommand is required. Printing help page:\n")
        parser.print_help()
