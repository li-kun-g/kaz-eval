#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-emit a generated item set with Russian instructions and Kazakh targets.

Only `question` changes; `id`, `answer` and `accept` are preserved byte-for-
byte, so the Kazakh and Russian conditions stay paired item-for-item.

    python3 ru_prompts.py data/kk_grammar_gen.jsonl data/kk_grammar_ru.jsonl
"""

import json
import sys
from pathlib import Path

TAIL = " Ответьте одним словом на казахском языке, без пояснений."

RU = {
    "plural": "Напишите казахское слово «%s» во множественном числе.",
    "gen":    "Напишите казахское слово «%s» в родительном падеже (кого? чего?).",
    "dat":    "Напишите казахское слово «%s» в дательном падеже (кому? куда?).",
    "acc":    "Напишите казахское слово «%s» в винительном падеже (кого? что?).",
    "loc":    "Напишите казахское слово «%s» в местном падеже (где? в чём?).",
    "abl":    "Напишите казахское слово «%s» в исходном падеже (откуда? от чего?).",
    "ins":    "Напишите казахское слово «%s» в творительном падеже (с кем? с чем?).",
    "poss3":  "Добавьте к казахскому слову «%s» притяжательный аффикс 3-го лица (его/её).",
    "gen_izafet": ("Поставьте казахское слово «%s» в нужную форму, чтобы "
                   "получилось словосочетание «___ суреті» (изображение кого/чего-либо)."),
}


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/kk_grammar_gen.jsonl")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "data/kk_grammar_ru.jsonl")

    out, skipped = [], set()
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        cat = it.get("category") or it.get("type")
        if cat not in RU:
            skipped.add(cat)
            continue
        it["question"] = RU[cat] % it["stem"] + TAIL
        out.append(json.dumps(it, ensure_ascii=False))

    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote %d items -> %s" % (len(out), dst))
    if skipped:
        print("skipped unknown categories: %s" % ", ".join(sorted(skipped)),
              file=sys.stderr)


if __name__ == "__main__":
    main()
