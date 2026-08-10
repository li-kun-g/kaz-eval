#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Treat blank completions as non-answers, not wrong answers."""
from pathlib import Path
import sys

TARGET = Path(sys.argv[1] if len(sys.argv) > 1 else "run_eval.py")
OLD = '''def is_error(rec: dict) -> bool:
    return str(rec.get("response", "")).startswith("__ERROR__")'''
NEW = '''def is_error(rec: dict) -> bool:
    """An empty completion is a non-answer, not a wrong answer.

    Excluding blanks keeps them out of the accuracy denominator and makes
    --resume retry them, which is what you want when an API intermittently
    returns nothing.
    """
    s = str(rec.get("response", "")).strip()
    return not s or s.startswith("__ERROR__")'''

src = TARGET.read_text(encoding="utf-8")
if "An empty completion is a non-answer" in src:
    print("already patched, nothing to do")
elif OLD in src:
    TARGET.write_text(src.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched %s" % TARGET)
else:
    sys.exit("could not find is_error() as expected -- patch NOT applied, "
             "file left untouched")
