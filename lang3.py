#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare one model across instruction languages, category by category."""
import json, sys
from collections import defaultdict
from pathlib import Path

MODEL = sys.argv[1] if len(sys.argv) > 1 else "gemma3-4b"
LANGS = [("kk", "Kazakh"), ("ru", "Russian"), ("en", "English")]
ORDER = ["plural", "gen", "dat", "acc", "loc", "abl", "ins", "poss3"]

def load(tag):
    p = Path("results/%s-%s.json" % (MODEL, tag))
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["records"]
            if str(r.get("response", "")).strip()
            and not str(r.get("response", "")).startswith("__ERROR__")]

cols, totals = {}, {}
for tag, _ in LANGS:
    recs = load(tag)
    if recs is None:
        continue
    b = defaultdict(lambda: [0, 0])
    for r in recs:
        k = b[r.get("category") or r.get("type")]
        k[0] += int(bool(r.get("correct")))
        k[1] += 1
    cols[tag] = {c: 100.0 * v[0] / v[1] for c, v in b.items()}
    totals[tag] = (sum(v[0] for v in b.values()), sum(v[1] for v in b.values()))

have = [t for t, _ in LANGS if t in cols]
print("%s, accuracy by instruction language\n" % MODEL)
print("%-10s%12s%12s%12s" % ("category", *[dict(LANGS)[t] for t in have]))
print("-" * (10 + 12 * len(have)))
for c in ORDER:
    if not any(c in cols[t] for t in have):
        continue
    print("%-10s" % c + "".join("%11.1f%%" % cols[t].get(c, float("nan")) for t in have))
print("-" * (10 + 12 * len(have)))
print("%-10s" % "OVERALL" + "".join("%11.1f%%" % (100.0 * totals[t][0] / totals[t][1])
                                    for t in have))
print()
print("n = %s" % ", ".join("%s %d" % (t, totals[t][1]) for t in have))
