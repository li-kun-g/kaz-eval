#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render PAPER.md to print-ready HTML. Open it, then Print > Save as PDF."""
import sys
from pathlib import Path
import markdown

src = Path(sys.argv[1] if len(sys.argv) > 1 else "PAPER.md")
dst = src.with_suffix(".html")

CSS = """
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt;
       line-height: 1.5; max-width: 42em; margin: 3em auto; padding: 0 2em;
       color: #111; }
h1 { font-size: 20pt; line-height: 1.25; margin-bottom: 0.2em; }
h2 { font-size: 14pt; margin-top: 1.8em; border-bottom: 1px solid #ddd;
     padding-bottom: 0.2em; }
h3 { font-size: 12pt; margin-top: 1.4em; }
table { border-collapse: collapse; margin: 1em 0; font-size: 10pt; }
th, td { border: 1px solid #bbb; padding: 4px 9px; text-align: left; }
th { background: #f2f2f2; }
td:not(:first-child), th:not(:first-child) { text-align: right; }
code { font-family: Menlo, monospace; font-size: 9.5pt;
       background: #f5f5f5; padding: 1px 3px; }
pre { background: #f7f7f7; padding: 0.8em; overflow-x: auto; font-size: 9pt;
      border-left: 3px solid #ddd; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3px solid #ccc; margin-left: 0; padding-left: 1em;
             color: #444; }
@media print { body { margin: 0; max-width: none; } h2 { page-break-after: avoid; }
               table, pre { page-break-inside: avoid; } }
"""

body = markdown.markdown(src.read_text(encoding="utf-8"),
                         extensions=["tables", "fenced_code", "sane_lists"])
dst.write_text("<!DOCTYPE html><html><head><meta charset='utf-8'>"
               "<title>%s</title><style>%s</style></head><body>%s</body></html>"
               % (src.stem, CSS, body), encoding="utf-8")
print("wrote %s" % dst)
