#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Noise floor: same model, same prompt language, different item samples."""
import json, statistics
from collections import defaultdict
from pathlib import Path

SEEDS = (7, 8, 9)

def load(s):
    p = Path("results/gemma3-4b-kk-seed%d.json" % s)
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["records"]
            if str(r.get("response", "")).strip()
            and not str(r.get("response", "")).startswith("__ERROR__")]

overall, percat = [], defaultdict(dict)
print("%-8s%9s%10s%9s%9s" % ("seed", "items", "answered", "correct", "acc"))
print("-" * 45)
for s in SEEDS:
    recs = load(s)
    ok = sum(1 for r in recs if r.get("correct"))
    acc = 100.0 * ok / len(recs)
    overall.append(acc)
    print("%-8d%9d%10d%9d%8.1f%%" % (s, len(recs), len(recs), ok, acc))
    buck = defaultdict(lambda: [0, 0])
    for r in recs:
        b = buck[r.get("category") or r.get("type")]
        b[0] += int(bool(r.get("correct")))
        b[1] += 1
    for c, (o, n) in buck.items():
        percat[c][s] = 100.0 * o / n
print("-" * 45)
print("OVERALL  mean %.1f%%   sd %.2f   range %.1f points"
      % (statistics.mean(overall), statistics.stdev(overall),
         max(overall) - min(overall)))
print()
print("%-10s%9s%9s%9s%9s" % ("category", "seed 7", "seed 8", "seed 9", "range"))
print("-" * 46)
for c in sorted(percat, key=lambda c: -(max(percat[c].values()) - min(percat[c].values()))):
    v = [percat[c].get(s) for s in SEEDS]
    print("%-10s%8.1f%%%8.1f%%%8.1f%%%8.1f" % (c, v[0], v[1], v[2], max(v) - min(v)))
print()
print("A difference smaller than a category's range across seeds is noise.")
