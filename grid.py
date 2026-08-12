#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Instruction language x item sample: means and observed ranges."""
import json, statistics
from collections import defaultdict
from pathlib import Path

MODEL = "gemma3-4b"
SEEDS = (7, 8, 9)
LANGS = [("kk", "Kazakh"), ("ru", "Russian"), ("en", "English")]
ORDER = ["plural", "gen", "dat", "acc", "loc", "abl", "ins", "poss3"]

def path_for(lang, seed):
    for cand in ("results/%s-%s-seed%d.json" % (MODEL, lang, seed),
                 "results/%s-%s.json" % (MODEL, lang)):
        p = Path(cand)
        if p.exists():
            if "seed" in cand or seed == 7:
                return p
    return None

def load(lang, seed):
    p = path_for(lang, seed)
    if p is None:
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return [r for r in d["records"]
            if str(r.get("response", "")).strip()
            and not str(r.get("response", "")).startswith("__ERROR__")]

overall = defaultdict(list)
percat = defaultdict(lambda: defaultdict(list))
for lang, _ in LANGS:
    for s in SEEDS:
        recs = load(lang, s)
        if recs is None:
            print("MISSING: %s seed %d" % (lang, s))
            continue
        ok = sum(1 for r in recs if r.get("correct"))
        overall[lang].append(100.0 * ok / len(recs))
        b = defaultdict(lambda: [0, 0])
        for r in recs:
            k = b[r.get("category") or r.get("type")]
            k[0] += int(bool(r.get("correct")))
            k[1] += 1
        for c, (o, n) in b.items():
            percat[lang][c].append(100.0 * o / n)

def fmt(vals):
    return "%5.1f +-%4.1f" % (statistics.mean(vals), (max(vals) - min(vals)) / 2)

print("gemma3:4b -- mean over 3 item samples, +- half the observed range\n")
print("%-9s%14s%14s%14s   %s" % ("category", "Kazakh", "Russian", "English", "RU vs EN"))
print("-" * 70)
for c in ORDER:
    row = "%-9s" % c
    means = {}
    for lang, _ in LANGS:
        v = percat[lang].get(c)
        row += "%14s" % (fmt(v) if v else "--")
        if v:
            means[lang] = statistics.mean(v)
    if "ru" in means and "en" in means:
        d = means["en"] - means["ru"]
        noise = max((max(percat[l][c]) - min(percat[l][c])) for l in ("ru", "en"))
        verdict = ("EN +%.1f" % d) if d > 0 else ("RU +%.1f" % -d)
        verdict += "" if abs(d) > noise else "  (within noise)"
        row += "   " + verdict
    print(row)
print("-" * 70)
row = "%-9s" % "OVERALL"
for lang, _ in LANGS:
    row += "%14s" % fmt(overall[lang])
print(row)
d = statistics.mean(overall["en"]) - statistics.mean(overall["ru"])
noise = max(max(overall[l]) - min(overall[l]) for l in ("ru", "en"))
print("\nEN - RU overall: %+.1f points, largest observed range %.1f -> %s"
      % (d, noise, "outside noise" if abs(d) > noise else "WITHIN NOISE"))
