import csv
import json
import os
import sys
import re
import yaml
import argparse
import logging
from dateutil import parser as dateparser
import datetime
from collections import defaultdict
from dateutil import tz as dtz

tz = dtz.gettz("America/New_York")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

class TxnPrinter:
    def __init__(self, name, date_idx, desc_idx, category_idx, debit_idx, negative_debit=False, prev_expenses={}):
        self.name = name
        self.date_idx = date_idx
        self.desc_idx = desc_idx
        self.category_idx = category_idx
        self.debit_idx = debit_idx
        self.prev_lut = prev_expenses
        self.matchers = []
        self.negative_debit = negative_debit

    def loadCategoryMap(self, path):
        with open(path, "r") as f:
            data = f.read()

        self.matchers = []
        for line in data.split("\n"):
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            field, category, regex_str = line.split(maxsplit=2)
            self.matchers.append((field, re.compile(regex_str), category))

    def printRow(self, row, interval_start, interval_end):
        date = dateparser.parse(row[self.date_idx]).astimezone(tz)
        if (date > interval_end) or (date < interval_start):
            log.info(f"Omit - {date} > {interval_end} or < {interval_start}")
            return False
        debit = row[self.debit_idx]
        if isinstance(debit, str):
            if debit.strip() == "":
                return False
            debit = float(debit)
        if self.negative_debit:
            debit = -debit
        if abs(debit) < 0.01:
            log.info(f"Omitting negligible charge: {row[self.desc_idx]} (${str(debit)})")
            return False

        if self.category_idx:
            category = row[self.category_idx]
        else:
            category = ''
        for (field, regex, cat) in self.matchers:
            field = field.lower()
            if (field == "desc" and regex.match(row[self.desc_idx])):
                category = cat
                break
            if (field == "category" and self.category_idx and regex.match(row[self.category_idx])):
                category = cat
                break
        if category == "OMIT":
            log.warning(f"Omitting {row[self.desc_idx]} (${str(debit)})")
            return False

        desc = row[self.desc_idx].replace("\"", "")
        out = f"{date.strftime('%Y-%m-%d')}, \"{desc}\", {category}, {debit}"
        if out in self.prev_lut:
            log.warning(f"Omit previously exported row: {out}")
            return False
        print(out)
        return True

def parse_csv(prev_lut, manifest, path, interval_start, inteval_end, filestats):
    with open(path, encoding='latin1') as f:
        log.info(f"Reading {path}")
        data = f.read().split('\n')

    if data[0].startswith("Note:"):
        header_idx = 2
    else:
        header_idx = 0

    hdr = dict([(v,i) for (i, v) in enumerate(data[header_idx].split(","))])
    printer = None
    for name, cfg in manifest.items():
      if 'match' not in cfg:
            continue
      if cfg['match'] in hdr.keys():
          log.info(f'Match on parser {name}')
          if cfg.get('pass', False):
            continue
          # 'Transaction Date', 'Posted Date', 'Card No.', 'Description', 'Category', 'Debit', 'Credit'
          printer = TxnPrinter(
              name,
              date_idx = hdr[cfg['hdr']['date']],
              desc_idx = hdr[cfg['hdr']['desc']],
              category_idx = hdr.get(cfg['hdr']['category']),
              debit_idx = hdr[cfg['hdr']['debit']],
              negative_debit = cfg['negative_debit'],
              prev_expenses = prev_lut,
          )
          printer.loadCategoryMap(os.path.join(os.path.dirname(__file__), f"./config/{cfg['rules']}"))
          break

    if printer is None:
        log.error(f"ERROR: origin of file {path} not resolved")
        sys.exit(1)

    for row in csv.reader(data[header_idx+1:]):
        if len(row) == 0:
            continue
        printed = printer.printRow(row, interval_start, interval_end)
        filestats[f"({printer.name})\t {path}"] += 1 if printed else 0

    return True



def parse_json(prev_lut, manifest, path, interval_start, inteval_end, filestats):
    with open(path, encoding='utf8') as f:
        data = json.loads(f.read())
    printer = None
    participant_id = None
    for name, cfg in manifest.items():
        if 'json_header_match' not in cfg or not data.get(cfg['json_header_match']):
            continue
        log.info(f"Match on parser {name}")
        printer = TxnPrinter(
                name,
                date_idx = cfg["hdr"]["date"],
                desc_idx = cfg["hdr"]["desc"],
                category_idx = cfg["hdr"]["category"],
                debit_idx = cfg["hdr"]["debit"],
                negative_debit = False,
                prev_expenses = prev_lut,
        )
        participant_id = cfg['participant_id']
        printer.loadCategoryMap(os.path.join(os.path.dirname(__file__), f"./config/{cfg['rules']}"))
        break

    if printer is None:
        log.error(f"ERROR: origin of file {path} not resolved")
        sys.exit(1)

    for row in data["expenses"]:
        # {"expenseDate":"2025-03-11T00:00:00.000Z",
        # "title":"groceries",
        # "category":{"grouping":"Uncategorized","name":"General"},
        # "amount":5918,
        # "paidById":"Xa5IFvRWcDOY9FPAaSrmI",
        # "paidFor":[{"participantId":"Xa5IFvRWcDOY9FPAaSrmI","shares":200},{"participantId":"Z6dxevKGICs39HibSzjOu","shares":100}],
        # "isReimbursement":false,
        # "splitMode":"BY_SHARES"}
        amount = row['amount']
        if row['splitMode'] == "BY_SHARES":
            self_shares = sum([p['shares'] for p in row['paidFor'] if p['participantId'] == participant_id])
            other_shares = sum([p['shares'] for p in row['paidFor'] if p['participantId'] != participant_id])
            amount = amount * (-other_shares if row['paidById'] == participant_id else self_shares) / (100 * (self_shares + other_shares))
            amount = round(amount, 2)
        row["computedAmount"] = amount
        row["category.name"] = row["category"]["name"]

        printed = printer.printRow(row, interval_start, interval_end)
        filestats[f"({printer.name})\t {path}"] += 1 if printed else 0

def parse_expenses(prev, paths, interval_start, interval_end):
    filestats = defaultdict(int)

    # Get all prior lines so we can ensure we're not duplicating anything
    with open(prev, encoding="utf8") as f:
        prev_lut = {l for l in f.read().split("\n")}
    log.info(f"Loaded {len(prev_lut)} previous entries to avoid")

    with open(os.path.join(os.path.dirname(__file__), "./config/manifest.yaml")) as f:
      manifest = yaml.safe_load(f.read())
    log.info(f"Loaded {len(manifest)} manifest entries")

    for path in paths:
        if path.endswith("out.csv"):
            log.warning(f"Skipping likely-dest-output out.csv file at {path}")
            continue
        ext = path.split('.')[-1].lower()
        if ext == "csv":
            parse_csv(prev_lut, manifest, path, interval_start, interval_end, filestats)
        elif ext == "json":
            parse_json(prev_lut, manifest, path, interval_start, interval_end, filestats)
        else:
            raise RuntimeError("Unknown file extension for file: " + path)
    return filestats

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse credit card and other statements to produced an organized transaction list")
    ap.add_argument("--prev", type=str, required=True, help="Path to previous output file, for deduplication")
    ap.add_argument('--paths', nargs='+', type=str, required=True, help='File paths to read')
    args = ap.parse_args(sys.argv[1:])

    # Interval a little bit before and after the month duration, to account for overlap
    interval_end = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(tz)
    while interval_end.day != 27:
        interval_end += datetime.timedelta(days=3)
    interval_start = interval_end - datetime.timedelta(days=30 + 7)

    log.info(f"Printing transactions from {interval_start} to {interval_end}, excluding any already listed in {args.prev}")

    filestats = parse_expenses(args.prev, args.paths, interval_start, interval_end)

    log.info(f"===================")
    log.info("Parsed {len(args.paths)} files:")
    for k,v in filestats.items():
        log.info(f"{k.ljust(40)}\t{v} item(s) parsed")
