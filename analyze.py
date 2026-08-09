#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Break a run_eval.py result file down by linguistic feature."""
import json, sys
from collections import defaultdict
from pathlib import Path

FRONT_V = set("әеөүі")
BACK_V = set("аоұы")
HARM_V = FRONT_V | BACK_V

SUFFIXES = {
    "plural": ["лар", "лер", "дар", "дер", "тар", "тер"],
    "gen":    ["ның", "нің", "дың", "дің", "тың", "тің"],
    "dat":    ["ға", "ге", "қа", "ке"],
    "acc":    ["ны", "ні", "ды", "ді", "ты", "ті"],
    "loc":    ["да", "де", "та", "те"],
    "abl":    ["дан", "ден", "нан", "нен", "тан", "тен"],
    "ins":    ["мен", "бен", "пен"],
    "poss3":  ["сы", "сі", "ы", "і"],
}

def is_front(w):
    for ch in reversed(w):
        if ch in HARM_V:
            return ch in FRONT_V
    return False

def end_class(w):
    c = w[-1]
    if c in "руй": return "ends р/у/й"
    if c == "л": return "ends л"
    if c in "мнң": return "ends м/н/ң"
    if c in "жз": return "ends ж/з"
    if c in HARM_V or c == "и": return "ends vowel"
    return "ends voiceless"

def category(r):
    return r.get("category") or r.get("type") or "?"

def gold_suffix(r):
    for s in sorted(SUFFIXES.get(category(r), []), key=len, reverse=True):
        if r["answer"].endswith(s):
            return s
    return "?"

def stem_of(r):
    return r.get("stem") or r.get("id", "-").split("-")[-1]

def table(title, b, note=None):
    if not b: return
    print(title)
    if note: print("  " + note)
    print("  %-20s%9s%7s%11s" % ("", "correct", "total", "accuracy"))
    print("  " + "-" * 47)
    for k in sorted(b, key=lambda k: (-b[k][1], k)):
        ok, n = b[k]
        print("  %-20s%9d%7d%10.1f%%" % (k, ok, n, 100 * ok / n if n else 0.0))
    print()

def analyze(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    key = doc.get("grader_key", "correct")
    recs = [r for r in doc["records"]
            if not str(r.get("response", "")).startswith("__ERROR__")]
    if not recs:
        print("%s: no answered records" % path); return
    hits = sum(int(bool(r.get(key))) for r in recs)
    print("\n" + "=" * 49)
    print("  %s   %d/%d = %.1f%%"
          % (doc.get("model", path), hits, len(recs), 100 * hits / len(recs)))
    print("=" * 49 + "\n")
    suf = defaultdict(lambda: [0, 0])
    harm = defaultdict(lambda: [0, 0])
    end = defaultdict(lambda: [0, 0])
    for r in recs:
        v = int(bool(r.get(key))); st = stem_of(r)
        for bucket, k in ((suf, "%-6s -%s" % (category(r), gold_suffix(r))),
                          (harm, "front vowel" if is_front(st) else "back vowel"),
                          (end, end_class(st))):
            bucket[k][0] += v
            bucket[k][1] += 1
    table("BY GOLD SUFFIX", suf,
          "if -лар >> -дар/-тар, the model is doing Turkish, not Kazakh")
    table("BY VOWEL HARMONY OF STEM", harm)
    table("BY STEM-FINAL SOUND", end,
          "assimilation picks the д- vs т- vs н- suffix onset")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: python3 analyze.py results/MODEL.json [...]")
    for p in sys.argv[1:]:
        analyze(p)
