#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
kaz_morph.py -- generate Kazakh nominal-morphology eval items as JSONL.

    python3 kaz_morph.py --generate 300 --seed 7 > data/kk_grammar_gen.jsonl
    python3 kaz_morph.py --generate 50 --seed 7 --tasks gen_izafet > data/kk_izafet.jsonl
    python3 kaz_morph.py --selftest
    python3 kaz_morph.py --list-tasks

REPRODUCIBILITY: the default task set is the original eight categories.
gen_izafet is opt-in via --tasks, so --generate 300 --seed 7 keeps producing
the exact same 300 items as before.
"""

import argparse
import json
import random
import sys

FRONT_V = set("әеөүі")
BACK_V = set("аоұы")
HARM_V = FRONT_V | BACK_V

VOICING = {"п": "б", "қ": "ғ", "к": "г"}


def is_front(word):
    """Harmony class = class of the last full vowel. у and и are skipped."""
    for ch in reversed(word):
        if ch in HARM_V:
            return ch in FRONT_V
    return False


def end_class(word):
    """Sound class of the stem-final segment, for allomorph selection."""
    c = word[-1]
    if c in "руй":
        return "RUY"
    if c == "л":
        return "L"
    if c in "мнң":
        return "NASAL"
    if c in "жз":
        return "JZ"
    if c in HARM_V or c == "и":
        return "V"
    return "VL"


PLURAL = {"V": ("лар", "лер"), "RUY": ("лар", "лер"),
          "L": ("дар", "дер"), "NASAL": ("дар", "дер"), "JZ": ("дар", "дер"),
          "VL": ("тар", "тер")}

GENITIVE = {"V": ("ның", "нің"), "NASAL": ("ның", "нің"),
            "RUY": ("дың", "дің"), "L": ("дың", "дің"), "JZ": ("дың", "дің"),
            "VL": ("тың", "тің")}

DATIVE = {"V": ("ға", "ге"), "RUY": ("ға", "ге"), "L": ("ға", "ге"),
          "NASAL": ("ға", "ге"), "JZ": ("ға", "ге"),
          "VL": ("қа", "ке")}

ACCUSATIVE = {"V": ("ны", "ні"),
              "RUY": ("ды", "ді"), "L": ("ды", "ді"),
              "NASAL": ("ды", "ді"), "JZ": ("ды", "ді"),
              "VL": ("ты", "ті")}

LOCATIVE = {"V": ("да", "де"), "RUY": ("да", "де"), "L": ("да", "де"),
            "NASAL": ("да", "де"), "JZ": ("да", "де"),
            "VL": ("та", "те")}

ABLATIVE = {"V": ("дан", "ден"), "RUY": ("дан", "ден"), "L": ("дан", "ден"),
            "JZ": ("дан", "ден"),
            "NASAL": ("нан", "нен"),
            "VL": ("тан", "тен")}

INSTRUMENTAL = {"V": ("мен", "мен"), "RUY": ("мен", "мен"),
                "L": ("мен", "мен"), "NASAL": ("мен", "мен"),
                "JZ": ("бен", "бен"),
                "VL": ("пен", "пен")}

TABLES = {"plural": PLURAL, "gen": GENITIVE, "dat": DATIVE, "acc": ACCUSATIVE,
          "loc": LOCATIVE, "abl": ABLATIVE, "ins": INSTRUMENTAL,
          "gen_izafet": GENITIVE}


def attach(stem, table):
    back, front = table[end_class(stem)]
    return stem + (front if is_front(stem) else back)


def possessive3(stem):
    """3rd-person possessive: -сы/-сі after vowels, -ы/-і otherwise."""
    if end_class(stem) == "V":
        return stem + ("сі" if is_front(stem) else "сы")
    body = stem
    if body[-1] in VOICING:
        body = body[:-1] + VOICING[body[-1]]
    return body + ("і" if is_front(stem) else "ы")


def inflect(stem, task):
    if task == "poss3":
        return possessive3(stem)
    return attach(stem, TABLES[task])


STEMS = [
    "кітап", "бала", "қала", "адам", "ат", "қыз", "жол", "тау", "қол", "жаз",
    "ұл", "сағат", "дос", "ағаш", "қасық", "бас", "жаңбыр", "ай", "алма",
    "сабақ", "жұмыс", "қалам", "орамал", "балық", "шаң", "аспан", "жылқы",
    "дала", "қар", "тас",
    "үй", "көл", "жер", "кісі", "іс", "көз", "тіс", "ел", "күн", "сөз",
    "мектеп", "дәптер", "бет", "ет", "терезе", "түн", "гүл", "кеш", "күш",
    "әже",
]

ONE_WORD = "Тек бір сөзбен жауап беріңіз, басқа ештеңе жазбаңыз."

CASE_PROMPTS = {
    "gen": "ілік септігінде (кімнің? ненің?)",
    "dat": "барыс септігінде (кімге? неге?)",
    "acc": "табыс септігінде (кімді? нені?)",
    "loc": "жатыс септігінде (кімде? неде?)",
    "abl": "шығыс септігінде (кімнен? неден?)",
    "ins": "көмектес септігінде (кіммен? немен?)",
}

DEFAULT_TASKS = ["plural", "gen", "dat", "acc", "loc", "abl", "ins", "poss3"]
EXTRA_TASKS = ["gen_izafet"]
ALL_TASKS = DEFAULT_TASKS + EXTRA_TASKS


def question_text(stem, task):
    if task == "plural":
        return "«%s» сөзінің көпше түрін жазыңыз. %s" % (stem, ONE_WORD)
    if task == "poss3":
        return ("«%s» сөзіне ІІІ жақтағы тәуелдік жалғауын жалғаңыз "
                "(оның ...). %s" % (stem, ONE_WORD))
    if task == "gen_izafet":
        return ("«%s» сөзін дұрыс формаға қойып, тіркесті толықтырыңыз: "
                "___ суреті. %s" % (stem, ONE_WORD))
    return "«%s» сөзін %s жазыңыз. %s" % (stem, CASE_PROMPTS[task], ONE_WORD)


def build_all(tasks):
    items = []
    for task in tasks:
        for stem in STEMS:
            ans = inflect(stem, task)
            items.append({
                "id": "kk-%s-%s" % (task, stem),
                "question": question_text(stem, task),
                "answer": ans,
                "accept": [ans],
                "type": task,
                "category": task,
                "stem": stem,
            })
    return items


GOLD = [
    ("кітап", "plural", "кітаптар"), ("жол", "plural", "жолдар"),
    ("жер", "plural", "жерлер"), ("тау", "plural", "таулар"),
    ("адам", "plural", "адамдар"), ("үй", "plural", "үйлер"),
    ("мектеп", "plural", "мектептер"), ("бала", "plural", "балалар"),
    ("қыз", "plural", "қыздар"), ("гүл", "plural", "гүлдер"),
    ("дос", "dat", "досқа"), ("қыз", "dat", "қызға"),
    ("мектеп", "dat", "мектепке"), ("үй", "dat", "үйге"),
    ("бала", "dat", "балаға"), ("сабақ", "dat", "сабаққа"),
    ("адам", "abl", "адамнан"), ("күн", "abl", "күннен"),
    ("дос", "abl", "достан"), ("бала", "abl", "баладан"),
    ("үй", "abl", "үйден"), ("қыз", "abl", "қыздан"),
    ("дос", "gen", "достың"), ("бала", "gen", "баланың"),
    ("күн", "gen", "күннің"), ("жол", "gen", "жолдың"),
    ("жер", "gen", "жердің"), ("адам", "gen", "адамның"),
    ("бала", "acc", "баланы"), ("дос", "acc", "досты"),
    ("үй", "acc", "үйді"), ("адам", "acc", "адамды"),
    ("дос", "loc", "доста"), ("мектеп", "loc", "мектепте"),
    ("үй", "loc", "үйде"), ("жол", "loc", "жолда"),
    ("кітап", "ins", "кітаппен"), ("қыз", "ins", "қызбен"),
    ("бала", "ins", "баламен"), ("жол", "ins", "жолмен"),
    ("көз", "ins", "көзбен"), ("үй", "ins", "үймен"),
    ("кітап", "poss3", "кітабы"), ("сабақ", "poss3", "сабағы"),
    ("мектеп", "poss3", "мектебі"), ("бала", "poss3", "баласы"),
    ("үй", "poss3", "үйі"), ("терезе", "poss3", "терезесі"),
    ("балық", "poss3", "балығы"), ("күн", "poss3", "күні"),
    ("бала", "gen_izafet", "баланың"), ("дос", "gen_izafet", "достың"),
    ("үй", "gen_izafet", "үйдің"), ("адам", "gen_izafet", "адамның"),
]


def selftest():
    bad = []
    for stem, task, want in GOLD:
        got = inflect(stem, task)
        if got != want:
            bad.append((stem, task, want, got))
    for stem, task, want, got in bad:
        print("FAIL %-10s %-11s expected %-14s got %s"
              % (stem, task, want, got), file=sys.stderr)
    print("selftest: %d/%d passed" % (len(GOLD) - len(bad), len(GOLD)),
          file=sys.stderr)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--generate", type=int, metavar="N",
                    help="number of items to emit as JSONL on stdout")
    ap.add_argument("--seed", type=int, default=0,
                    help="shuffle seed, for reproducible sets")
    ap.add_argument("--tasks", default=",".join(DEFAULT_TASKS),
                    help="comma-separated task names (default: the original "
                         "eight categories, so --seed 7 stays reproducible)")
    ap.add_argument("--list-tasks", action="store_true",
                    help="print available task names and exit")
    ap.add_argument("--selftest", action="store_true",
                    help="check the rule tables against hand-verified forms")
    args = ap.parse_args()

    if args.list_tasks:
        print("default: %s" % ", ".join(DEFAULT_TASKS))
        print("extra:   %s" % ", ".join(EXTRA_TASKS))
        return

    if args.selftest:
        sys.exit(selftest())

    if not args.generate:
        ap.error("give --generate N (or --selftest / --list-tasks)")

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    unknown = [t for t in tasks if t not in ALL_TASKS]
    if unknown:
        ap.error("unknown task(s): %s (see --list-tasks)" % ", ".join(unknown))

    if selftest() != 0:
        sys.exit("rule tables are wrong; refusing to generate")

    items = build_all(tasks)
    if args.generate > len(items):
        print("warning: only %d unique items exist for tasks %s; emitting all"
              % (len(items), ",".join(tasks)), file=sys.stderr)
        args.generate = len(items)

    random.Random(args.seed).shuffle(items)
    for it in items[: args.generate]:
        print(json.dumps(it, ensure_ascii=False))


if __name__ == "__main__":
    main()
