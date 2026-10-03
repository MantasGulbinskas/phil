#!/usr/bin/env python3
"""Compact shortlist of scan.py output for unscreened selection.

Usage: python3 core/scan.py ... > f.jsonl
       python3 strategy/tools/shortlist.py f.jsonl [min_liquidity]

Why: when the screener quota is exhausted (2026-10-03, 150/150 for the UTC
day) selection falls back to reading scan output by hand, and a 1 MB JSONL
dump is unreadable. Drops line-constructed shapes (spreads, totals, up/down)
and near-certain prices, then prints one line per market sorted by end date.
"""
import json
import sys

SKIP = ("Spread", "O/U", "Over ", "Up or Down", "Total", "Handicap")


def main():
    path = sys.argv[1]
    min_liq = float(sys.argv[2]) if len(sys.argv) > 2 else 5000.0
    rows = []
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            q = r.get("question", "")
            prices = r.get("outcome_prices") or []
            if any(s in q for s in SKIP) or not prices:
                continue
            if max(prices) > 0.95 or min(prices) < 0.05:
                continue
            if float(r.get("liquidity") or 0) < min_liq:
                continue
            rows.append(r)
    rows.sort(key=lambda r: r.get("end_date") or "")
    for r in rows:
        print(r["end_date"][:16], r["market_id"], r["question"][:90],
              r["outcome_prices"], int(float(r.get("liquidity") or 0)))


if __name__ == "__main__":
    main()
