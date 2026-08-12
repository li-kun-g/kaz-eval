#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-emit an item set with English instructions and Kazakh targets."""
import json, sys
from pathlib import Path

TAIL = " Answer with one Kazakh word only, no explanation."

EN = {
    "plural": 'Write the Kazakh word "%s" in the plural.',
    "gen":    'Write the Kazakh word "%s" in the genitive case (whose?).',
    "dat":    'Write the Kazakh word "%s" in the dative case (to whom? to where?).',
    "acc":    'Write the Kazakh word "%s" in the accusative case (whom? what?).',
    "loc":    'Write the Kazakh word "%s" in the locative case (where? in what?).',
    "abl":    'Write the Kazakh word "%s" in the ablative case (from where? from what?).',
    "ins":    'Write the Kazakh word "%s" in the instrumental case (with whom? with what?).',
    "poss3":  'Add the 3rd-person possessive suffix to the Kazakh word "%s" (his/her/its).',
    "gen_izafet": ('Put the Kazakh word "%s" in the form needed to complete the '
                   'phrase "___ суреті" (a picture of something).'),
}

def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "data/kk_grammar_gen.jsonl")
    dst = Path(sys.argv[2] if len(sys.argv) > 2 else "data/kk_grammar_en.jsonl")
    out, skipped = [], set()
    for line in src.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        it = json.loads(line)
        cat = it.get("category") or it.get("type")
        if cat not in EN:
            skipped.add(cat)
            continue
        it["question"] = EN[cat] % it["stem"] + TAIL
        out.append(json.dumps(it, ensure_ascii=False))
    dst.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("wrote %d items -> %s" % (len(out), dst))
    if skipped:
        print("skipped: %s" % ", ".join(sorted(skipped)), file=sys.stderr)

if __name__ == "__main__":
    main()
