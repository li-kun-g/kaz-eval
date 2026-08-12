#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepend k worked examples to each item, in the item's own instruction language."""

import json
import sys
from pathlib import Path

import kaz_morph
from ru_prompts import RU, TAIL as RU_TAIL
from en_prompts import EN, TAIL as EN_TAIL

DEMOS = ["бала", "үй", "дос", "қыз", "мектеп", "жол"]


def question_for(stem, cat, lang):
    if lang == "kk":
        return kaz_morph.question_text(stem, cat)
    if lang == "ru":
        return RU[cat] % stem + RU_TAIL
    if lang == "en":
        return EN[cat] % stem + EN_TAIL
    raise ValueError("unknown language: %s" % lang)


def build(item, lang, k):
    cat = item.get("category") or item.get("type")
    target = item["stem"]
    gold = kaz_morph.inflect(target, cat)
    shots = []
    for d in DEMOS:
        if len(shots) >= k:
            break
        if d == target:
            continue
        demo_answer = kaz_morph.inflect(d, cat)
        if demo_answer == gold or gold in demo_answer or demo_answer in gold:
            continue
        shots.append((question_for(d, cat, lang), demo_answer))
    blocks = ["%s\n%s" % (q, a) for q, a in shots]
    blocks.append(question_for(target, cat, lang))
    return "\n\n".join(blocks)


def main():
    if len(sys.argv) < 5:
        sys.exit("usage: fewshot.py SRC DST {kk|ru|en} K")
    src, dst, lang, k = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], int(sys.argv[4])
    out = []
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        it["question"] = build(it, lang, k)
        it["shots"] = k
        out.append(json.dumps(it, ensure_ascii=False))
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote %d items (%d-shot, %s) -> %s" % (len(out), k, lang, dst))


if __name__ == "__main__":
    main()
