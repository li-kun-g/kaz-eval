#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-emit the grammar set with Russian instructions, Kazakh targets."""
import json
from pathlib import Path

RU = {
 "plural": "Напишите казахское слово «%s» во множественном числе.",
 "gen":    "Напишите казахское слово «%s» в родительном падеже (кого? чего?).",
 "dat":    "Напишите казахское слово «%s» в дательном падеже (кому? куда?).",
 "acc":    "Напишите казахское слово «%s» в винительном падеже (кого? что?).",
 "loc":    "Напишите казахское слово «%s» в местном падеже (где? в чём?).",
 "abl":    "Напишите казахское слово «%s» в исходном падеже (откуда? от чего?).",
 "ins":    "Напишите казахское слово «%s» в творительном падеже (с кем? с чем?).",
 "poss3":  "Добавьте к казахскому слову «%s» притяжательный аффикс 3-го лица (его/её).",
}
TAIL = " Ответьте одним словом на казахском языке, без пояснений."

src = Path("data/kk_grammar_gen.jsonl")
dst = Path("data/kk_grammar_ru.jsonl")
out = []
for line in src.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    it = json.loads(line)
    it["question"] = RU[it["category"]] % it["stem"] + TAIL
    out.append(json.dumps(it, ensure_ascii=False))
dst.write_text("\n".join(out) + "\n", encoding="utf-8")
print("wrote %d items -> %s" % (len(out), dst))
