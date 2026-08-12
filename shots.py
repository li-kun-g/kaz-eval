#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Effect of in-context examples, by instruction language and category."""
import json
from collections import defaultdict
from pathlib import Path

COLS = [("gemma3-4b-kk", "KK 0-shot"), ("gemma3-4b-kk_1shot", "KK 1-shot"),
        ("gemma3-4b-kk_5shot", "KK 5-shot"),
        ("gemma3-4b-ru", "RU 0-shot"), ("gemma3-4b-ru_5shot", "RU 5-shot")]
ORDER = ["plural", "gen", "dat", "acc", "loc", "abl", "ins", "poss3"]

def load(stem):
    p = Path("results/%s.json" % stem)
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["records"]
            if str(r.get("response", "")).strip()
            and not str(r.get("response", "")).startswith("__ERROR__")]

cols, tot = {}, {}
for stem, label in COLS:
    recs = load(stem)
    if recs is None:
        print("missing: %s" % stem)
        continue
    b = defaultdict(lambda: [0, 0])
    for r in recs:
        k = b[r.get("category") or r.get("type")]
        k[0] += int(bool(r.get("correct")))
        k[1] += 1
    cols[label] = {c: 100.0 * v[0] / v[1] for c, v in b.items()}
    tot[label] = 100.0 * sum(v[0] for v in b.values()) / sum(v[1] for v in b.values())

have = [l for _, l in COLS if l in cols]
print("gemma3:4b -- effect of in-context examples\n")
print("%-9s" % "category" + "".join("%12s" % h for h in have))
print("-" * (9 + 12 * len(have)))
for c in ORDER:
    print("%-9s" % c + "".join("%11.1f%%" % cols[h].get(c, float("nan")) for h in have))
print("-" * (9 + 12 * len(have)))
print("%-9s" % "OVERALL" + "".join("%11.1f%%" % tot[h] for h in have))
print()
if "KK 0-shot" in tot and "KK 5-shot" in tot:
    print("Kazakh 0-shot -> 5-shot: %+.1f points" % (tot["KK 5-shot"] - tot["KK 0-shot"]))
if "RU 0-shot" in tot and "RU 5-shot" in tot:
    print("Russian 0-shot -> 5-shot: %+.1f points" % (tot["RU 5-shot"] - tot["RU 0-shot"]))
if all(k in tot for k in ("KK 0-shot", "RU 0-shot", "KK 5-shot", "RU 5-shot")):
    print("KK-RU gap: %.1f points at 0-shot, %.1f points at 5-shot"
          % (tot["RU 0-shot"] - tot["KK 0-shot"], tot["RU 5-shot"] - tot["KK 5-shot"]))
