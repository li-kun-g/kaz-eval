#!/usr/bin/env python3
"""
run_eval.py — score any chat model on your Kazakh evaluation set.

Works with anything speaking the OpenAI chat-completions protocol (OpenAI,
Together, Groq, OpenRouter, local vLLM, Ollama), plus Google's native Gemini
endpoint via --provider gemini.

Design rule: a failure to ANSWER is never scored as a WRONG answer.
Rate limits, truncated generations and reasoning-only replies are recorded as
errors and excluded from accuracy. Conflating them silently understates a
model and sends you off building the wrong thing.

Usage
-----
    # local, no quota (recommended for iteration)
    python run_eval.py --model gemma3:4b \\
        --base-url http://localhost:11434/v1 --api-key ollama \\
        --data data/kk_grammar_gen.jsonl --max-tokens 64

    # Google (native endpoint — required for 'AQ.'-format keys)
    python run_eval.py --provider gemini --api-key $GOOGLE_KEY \\
        --model gemini-3.5-flash --data data/kk_grammar_gen.jsonl --sleep 6

    # no account whatsoever
    python run_eval.py --dry-run
    python run_eval.py --score-file manual/answers.txt --model chatgpt-web

    python run_eval.py --compare results/*.json
"""

# Keeps `str | None` annotations legal on Python 3.9 (macOS system Python).
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).parent / "data" / "kk_seed_eval.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

SYSTEM_PROMPT = (
    "Сен қазақ тілінде жауап беретін көмекшісің. "
    "Сұраққа қысқа әрі нақты жауап бер. Артық түсіндірме жазба."
)

JUDGE_PROMPT = """You are grading a Kazakh-language exam answer.

Question: {question}
Reference answer: {answer}
Model's answer: {response}

Is the model's answer factually correct and responsive to the question?
Ignore differences in wording, script, verbosity, or language of response.
Judge only correctness of content.

Reply with exactly one word: CORRECT or INCORRECT"""


# ---------------------------------------------------------------- normalizing
_PUNCT = dict.fromkeys(
    i for i in range(sys.maxunicode) if unicodedata.category(chr(i)).startswith("P")
)


def normalize(s: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace, unify lookalikes."""
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.replace("ѐ", "е").replace("ё", "е").replace("i", "і")
    s = s.translate(_PUNCT)
    return re.sub(r"\s+", " ", s).strip()


def strip_question_echo(question: str, response: str, accepts: list[str]) -> str:
    """Remove words the model merely parroted back from the question.

    Without this, substring grading is badly broken: for "Қазақстанның
    астанасы қай қала?" the reply "...астанасы — Мәскеу" scored CORRECT,
    because the echoed question word "астанасы" contains the accepted answer
    "астана" as a substring.

    The exception matters too: naively dropping every question word would
    fail a correct "22 наурыз" for "Наурыз ... қай күні?". So a question word
    is stripped only if it is not itself an accepted answer token.
    "астанасы" != "астана", so it goes; "наурыз" stays.
    """
    accept_tokens = {w for a in accepts for w in a.split()}
    q_words = {w for w in normalize(question).split() if w not in accept_tokens}
    return " ".join(w for w in normalize(response).split() if w not in q_words)


def substring_grade(item: dict, response: str) -> bool:
    """Match `accept` phrases against the response, question-echo removed."""
    accepts = [normalize(a) for a in item.get("accept", []) if a.strip()]
    if not accepts:
        return False
    resp = strip_question_echo(item["question"], response, accepts)
    if not resp:
        return False
    if item.get("require_all"):
        return all(a in resp for a in accepts)
    return any(a in resp for a in accepts)


def is_error(rec: dict) -> bool:
    return str(rec.get("response", "")).startswith("__ERROR__")


_THINK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.S | re.I)
_THINK_OPEN = re.compile(r"<(think|thinking|reasoning)>.*\Z", re.S | re.I)


def strip_reasoning(text: str) -> str:
    """Remove chain-of-thought blocks before grading.

    Reasoning models (Qwen3, DeepSeek-R1, ...) emit <think>...</think> ahead
    of the answer. Grading that text is actively wrong: a model that muses
    "maybe үйдің? no, үйнің" and then answers incorrectly would still match
    on the substring inside its own reasoning. Only the final answer counts.

    Also drops an unclosed <think> when generation was truncated mid-thought.
    """
    out = _THINK.sub(" ", text)
    out = _THINK_OPEN.sub(" ", out)
    return out.strip()


# ------------------------------------------------------------------ inference
# Retrying these is pointless — a bad model name or key will never succeed,
# and retrying just burns free-tier quota until you start getting 429s.
PERMANENT_CODES = {400, 401, 403, 404}


class PermanentError(RuntimeError):
    """Config problem or exhausted quota. Abort the run, don't retry."""


def _status(exc) -> int | None:
    for obj in (exc, getattr(exc, "response", None)):
        code = getattr(obj, "status_code", None) or getattr(obj, "code", None)
        if isinstance(code, int):
            return code
    return None


def _retry_after(exc) -> float | None:
    """Google returns its own RetryInfo: {"retryDelay": "37s"}. Obey it."""
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', str(exc))
    return float(m.group(1)) if m else None


def _is_rate_limit(exc) -> bool:
    return _status(exc) == 429 or "429" in str(exc)[:400]


_QUOTA_HINTS = ("exceeded your current quota", "billing details",
                "perday", "requests per day", "daily limit", "quota_exceeded")


def _is_quota_exhausted(exc) -> bool:
    """Distinguish 'slow down' from 'you are done for today'.

    Both arrive as HTTP 429 but need opposite responses. A per-minute limit
    carries a short retryDelay and waiting fixes it. A daily quota has no
    useful retryDelay — and every retry burns another request against the
    quota you already exhausted.
    """
    if not _is_rate_limit(exc):
        return False
    delay = _retry_after(exc)
    if delay is not None:
        return delay > 300
    low = str(exc).lower()
    return any(h in low for h in _QUOTA_HINTS)


REASONING_ONLY = ("__ERROR__ reasoning-only response (%d chars, no answer "
                  "emitted). Raise --max-tokens, or use a non-reasoning model "
                  "such as gemma3:4b / qwen2.5:3b.")


def make_openai_backend(base_url: str | None, api_key: str | None,
                        max_tokens: int = 1000, no_think: bool = False):
    try:
        from openai import OpenAI
    except ImportError:
        sys.exit("pip install openai")
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("Set OPENAI_API_KEY or pass --api-key")
    client = OpenAI(base_url=base_url, api_key=key)

    # Ollama accepts {"think": false} as an extra body field; older builds
    # reject unknown fields, so drop it permanently on the first refusal.
    state = {"extra": {"think": False} if no_think else {}}

    def call(model: str, question: str, system: str) -> str:
        # Qwen3 also honours an inline /no_think switch. Belt and braces: a
        # 4B model deliberating over a case ending is slow and, as we found,
        # often burns the entire token budget without ever answering.
        prompt = question + (" /no_think" if no_think else "")
        kwargs = dict(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=0, max_tokens=max_tokens,
        )
        try:
            if state["extra"]:
                kwargs["extra_body"] = dict(state["extra"])
            r = client.chat.completions.create(**kwargs)
        except Exception as e:
            if state["extra"] and _status(e) in (400, 422):
                state["extra"] = {}          # server dislikes it; stop sending
                kwargs.pop("extra_body", None)
                r = client.chat.completions.create(**kwargs)
            elif _status(e) in PERMANENT_CODES:
                raise PermanentError("%s: %s" % (type(e).__name__, e)) from e
            else:
                raise
        raw = r.choices[0].message.content or ""
        call.last_raw = raw
        clean = strip_reasoning(raw)
        # Reasoning filled the budget and no answer was emitted. That is a
        # truncated generation, NOT a wrong answer — scoring it as wrong
        # understates the model exactly like counting 429s as failures.
        if raw.strip() and not clean:
            return REASONING_ONLY % len(raw)
        return clean

    call.last_raw = ""
    return call


def make_gemini_backend(api_key: str | None, max_tokens: int = 1000,
                        no_think: bool = False):
    """Google's NATIVE endpoint.

    Needed because API keys in the newer 'AQ.' format are rejected by
    Google's OpenAI-compatible endpoint but work fine here. urllib, no deps.
    """
    import urllib.error
    import urllib.request

    key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        sys.exit("Set GOOGLE_API_KEY or pass --api-key")
    root = "https://generativelanguage.googleapis.com/v1beta"

    def _post(url: str, body: dict) -> dict:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            if e.code in PERMANENT_CODES:
                raise PermanentError("HTTP %d: %s" % (e.code, detail)) from e
            raise RuntimeError("HTTP %d: %s" % (e.code, detail)) from e

    def call(model: str, question: str, system: str) -> str:
        body = {
            "contents": [{"role": "user", "parts": [{"text": question}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": max_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = _post("%s/models/%s:generateContent?key=%s" % (root, model, key), body)
        for cand in data.get("candidates", []):
            parts = cand.get("content", {}).get("parts", [])
            # Gemini flags reasoning parts with "thought": true — skip them.
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            call.last_raw = text
            if text.strip():
                clean = strip_reasoning(text)
                return clean if clean else REASONING_ONLY % len(text)
        return ""

    def list_models():
        req = urllib.request.Request("%s/models?key=%s" % (root, key))
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            sys.exit("Could not list models: HTTP %d: %s"
                     % (e.code, e.read().decode("utf-8", "replace")[:300]))
        names = sorted(
            m["name"].split("/", 1)[-1] for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", []))
        print("\n%d models available to your key:\n" % len(names))
        for n in names:
            print("  " + n)
        print("\nPass one with --model.\n")

    call.last_raw = ""
    call.list_models = list_models
    return call


def ask(backend, model: str, question: str, system: str,
        retries: int = 5, sleep: float = 0.0) -> str:
    """Retry transient failures only. PermanentError propagates to abort.

    Rate limits need far longer backoff than other errors: free tiers meter
    per MINUTE, so a 2-second retry is guaranteed to fail again. Exhausted
    DAILY quota is not retried at all — no amount of waiting helps today.
    """
    for attempt in range(retries):
        try:
            out = backend(model, question, system)
            if sleep:
                time.sleep(sleep)
            return out
        except PermanentError:
            raise
        except Exception as e:
            if _is_quota_exhausted(e):
                raise PermanentError(
                    "daily quota exhausted for this key/model:\n  "
                    + " ".join(str(e).split())[:180]) from e
            if attempt == retries - 1:
                flat = " ".join(str(e).split())[:150]
                return "__ERROR__ %s: %s" % (type(e).__name__, flat)
            if _is_rate_limit(e):
                wait = _retry_after(e) or min(60.0, 15.0 * (attempt + 1))
                print("      rate limited, waiting %.0fs..." % wait, flush=True)
            else:
                wait = 2 ** attempt + 1
            time.sleep(wait)
    return "__ERROR__ unreachable"


# -------------------------------------------------------------------- display
def report(records: list[dict], model: str, grader_key: str):
    """Accuracy is computed over ANSWERED items only.

    An API error, a truncated generation, or a reasoning-only reply is not a
    wrong answer. A run with 4 rate-limit errors out of 20 reads as 80% when
    the true score on answered items is 100%. That distinction decides what
    you build next, so it has to be visible.
    """
    answered = [r for r in records if not is_error(r)]
    errors = [r for r in records if is_error(r)]

    by_cat = defaultdict(lambda: [0, 0])
    for r in answered:
        c = by_cat[r["category"]]
        c[1] += 1
        c[0] += int(bool(r[grader_key]))

    print("\n%s\n  %s   (grading: %s)\n%s" % ("=" * 58, model, grader_key, "=" * 58))
    print("%-16s%9s%7s%11s" % ("category", "correct", "total", "accuracy"))
    print("-" * 58)
    for cat in sorted(by_cat):
        ok, n = by_cat[cat]
        print("%-16s%9d%7d%10.1f%%" % (cat, ok, n, 100 * ok / n))
    total_ok = sum(v[0] for v in by_cat.values())
    total_n = sum(v[1] for v in by_cat.values())
    print("-" * 58)
    score = total_ok / total_n if total_n else 0.0
    print("%-16s%9d%7d%10.1f%%" % ("OVERALL", total_ok, total_n, 100 * score))

    if errors:
        pct = len(errors) / len(records)
        print("\n  %d of %d items errored and are EXCLUDED from the score above."
              % (len(errors), len(records)))
        print("  " + " ".join(str(errors[0]["response"]).split())[:120])
        if pct > 0.1:
            print("\n  WARNING: %.0f%% of items failed. Fix that and re-run "
                  "with --resume before trusting this number." % (100 * pct))
    print()

    # Subtask breakdown — for grammar runs this is where the signal is.
    subs = defaultdict(lambda: [0, 0])
    for r in answered:
        if r.get("subtask"):
            s = subs[r["subtask"]]
            s[1] += 1
            s[0] += int(bool(r[grader_key]))
    if len(subs) > 1:
        print("%-16s%9s%7s%11s" % ("subtask", "correct", "total", "accuracy"))
        print("-" * 58)
        for k in sorted(subs, key=lambda k: subs[k][0] / subs[k][1]):
            ok, n = subs[k]
            print("%-16s%9d%7d%10.1f%%" % (k, ok, n, 100 * ok / n))
        print()

    wrong = [r for r in answered if not r[grader_key]]
    if wrong:
        print("Wrong answers (%d) — read these, they are your product spec:\n"
              % len(wrong))
        for r in wrong[:15]:
            print("  [%s] %s" % (r["id"], r["question"][:66]))
            print("      expected: %s" % r["answer"][:66])
            print("      got:      %s\n"
                  % " ".join(str(r["response"]).split())[:66])
        if len(wrong) > 15:
            print("  ... and %d more (see the saved JSON)\n" % (len(wrong) - 15))
    elif answered:
        print("No wrong answers on the items that were answered.\n")
    return score


def write_manual_pack(items: list[dict], path: Path) -> None:
    """Write a numbered question list to paste into any free chatbot web UI."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "Төмендегі сұрақтарға қазақ тілінде жауап беріңіз.",
        "Әр жауапты жаңа жолға, нөмірімен жазыңыз. Тек жауабын жазыңыз.",
        "",
    ]
    lines += ["%d. %s" % (n, it["question"]) for n, it in enumerate(items, 1)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    ans = path.parent / "answers.txt"
    if not ans.exists():
        ans.write_text("\n".join("%d." % n for n in range(1, len(items) + 1)) + "\n",
                       encoding="utf-8")

    print("\nWrote %d questions -> %s" % (len(items), path))
    print("Answer template            -> %s" % ans)
    print("\n  1. Paste the questions into any chatbot (free web UI is fine).")
    print("  2. Save its replies into %s, one per numbered line." % ans)
    print("  3. python run_eval.py --score-file %s --model <name-it-yourself>\n" % ans)


def read_manual_answers(path: Path, n_items: int) -> list[str]:
    """Parse '1. answer' lines. Falls back to positional order if unnumbered."""
    answers = [""] * n_items
    leftovers = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^\s*(\d+)\s*[.)\]]\s*(.*)$", line)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < n_items:
                answers[idx] = m.group(2).strip()
        else:
            leftovers.append(line)

    if not any(answers) and leftovers:
        for i, line in enumerate(leftovers[:n_items]):
            answers[i] = line
    return answers


def compare(paths: list[str]):
    runs = []
    for p in paths:
        d = json.loads(Path(p).read_text(encoding="utf-8"))
        runs.append((d["model"], {r["id"]: r for r in d["records"]},
                     d.get("grader_key", "correct")))

    ids = sorted(set().union(*[set(r[1]) for r in runs]))
    names = [r[0][:16] for r in runs]
    w = max(18, max(len(n) for n in names) + 2)
    print("\n%-26s%s" % ("item", "".join("%*s" % (w, n) for n in names)))
    print("-" * (26 + w * len(names)))
    for i in ids:
        cells = ""
        for name, run, g in runs:
            if i not in run:
                cell = "-"
            elif is_error(run[i]):
                cell = "err"
            else:
                cell = "OK" if run[i][g] else "miss"
            cells += "%*s" % (w, cell)
        print("%-26s%s" % (i, cells))
    print("-" * (26 + w * len(names)))

    cells = ""
    for name, run, g in runs:
        ans = [r for r in run.values() if not is_error(r)]
        pct = sum(bool(r[g]) for r in ans) / len(ans) if ans else 0.0
        cells += "%*s" % (w, "%.1f%%" % (100 * pct))
    print("%-26s%s" % ("SCORE (answered only)", cells))

    cells = "".join("%*d" % (w, sum(is_error(r) for r in run.values()))
                    for _, run, _ in runs)
    print("%-26s%s\n" % ("errored (excluded)", cells))


# ----------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model")
    ap.add_argument("--base-url", default=None, help="e.g. http://localhost:11434/v1")
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--grader", choices=["substring", "judge", "both"],
                    default="substring")
    ap.add_argument("--judge-model", default="gpt-4o")
    ap.add_argument("--system", default=SYSTEM_PROMPT)
    ap.add_argument("--limit", type=int, help="only first N items (smoke test)")
    ap.add_argument("--compare", nargs="+", help="compare saved result JSON files")
    ap.add_argument("--dry-run", action="store_true",
                    help="no API: write a question pack to paste into any chatbot")
    ap.add_argument("--score-file", metavar="FILE",
                    help="no API: grade answers you collected by hand")
    ap.add_argument("--provider", choices=["openai", "gemini"], default="openai",
                    help="'gemini' uses Google's native endpoint — required for "
                         "newer 'AQ.'-format Google keys")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds between requests; use 6 on Gemini free tier")
    ap.add_argument("--resume", action="store_true",
                    help="reuse answers already saved in results/<model>.json")
    ap.add_argument("--list-models", action="store_true",
                    help="list models your key can actually use, then exit")
    ap.add_argument("--max-tokens", type=int, default=1000,
                    help="one-word answers need ~64; reasoning models need "
                         "1500+ or they never reach the answer")
    ap.add_argument("--no-think", action="store_true",
                    help="disable chain-of-thought (Qwen3 etc): sends "
                         "think=false and appends /no_think")
    args = ap.parse_args()

    if args.list_models:
        if args.provider != "gemini":
            sys.exit("--list-models currently supports --provider gemini")
        make_gemini_backend(args.api_key).list_models()
        return

    if args.compare:
        compare(args.compare)
        return

    data_path = Path(args.data)
    if not data_path.exists():
        sys.exit("No such data file: %s\n\nGenerate the grammar set with:\n"
                 "  python kaz_morph.py --generate 300 --seed 7 > "
                 "data/kk_grammar_gen.jsonl" % data_path)

    items = [json.loads(l) for l in
             data_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        items = items[: args.limit]

    if args.dry_run:
        write_manual_pack(items, Path(__file__).parent / "manual" / "questions.txt")
        return

    if not args.model:
        ap.error("--model is required (or use --compare / --dry-run)")

    print("Loaded %d items from %s" % (len(items), args.data))

    # ---- offline grading of hand-collected answers ----
    if args.score_file:
        answers = read_manual_answers(Path(args.score_file), len(items))
        blank = sum(1 for a in answers if not a)
        if blank:
            print("warning: %d/%d answers are blank (they count as incorrect)"
                  % (blank, len(items)))
        records = [{**it, "response": a, "substring": substring_grade(it, a),
                    "judge": None, "correct": substring_grade(it, a)}
                   for it, a in zip(items, answers)]
        score = report(records, args.model, "correct")
        RESULTS_DIR.mkdir(exist_ok=True)
        slug = re.sub(r"[^A-Za-z0-9._-]", "-", args.model)
        out = RESULTS_DIR / ("%s.json" % slug)
        out.write_text(json.dumps(
            {"model": args.model, "grader": "manual", "grader_key": "correct",
             "score": score, "complete": True, "system_prompt": None,
             "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Saved -> %s" % out)
        return

    if args.provider == "gemini":
        backend = make_gemini_backend(args.api_key, args.max_tokens, args.no_think)
    else:
        backend = make_openai_backend(args.base_url, args.api_key,
                                      args.max_tokens, args.no_think)
    judge = backend if args.grader in ("judge", "both") else None

    RESULTS_DIR.mkdir(exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", args.model)
    out = RESULTS_DIR / ("%s.json" % slug)

    def save(records, score=None):
        """Write partial or final results. Called often, and on interrupt."""
        out.write_text(json.dumps(
            {"model": args.model, "grader": args.grader, "grader_key": "correct",
             "score": score, "complete": score is not None,
             "system_prompt": args.system, "records": records},
            ensure_ascii=False, indent=2), encoding="utf-8")

    # Resume: reuse answers already collected, retry only errors and new items.
    done = {}
    if args.resume and out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
            done = {r["id"]: r for r in prev.get("records", []) if not is_error(r)}
            print("Resuming from %s: %d items already answered, %d to go"
                  % (out.name, len(done), len(items) - len(done)))
        except (json.JSONDecodeError, KeyError) as e:
            print("Could not read %s (%s); starting fresh" % (out.name, e))

    records = []
    consecutive_errors = 0
    t0 = time.time()
    try:
        for n, item in enumerate(items, 1):
            if item["id"] in done:
                records.append(done[item["id"]])
                continue

            resp = ask(backend, args.model, item["question"], args.system,
                       sleep=args.sleep)

            errored = resp.startswith("__ERROR__")
            consecutive_errors = consecutive_errors + 1 if errored else 0

            sub = substring_grade(item, resp)

            jud = None
            if not errored and (args.grader == "judge"
                                or (args.grader == "both" and not sub)):
                verdict = ask(
                    judge, args.judge_model,
                    JUDGE_PROMPT.format(question=item["question"],
                                        answer=item["answer"], response=resp),
                    "You are a strict but fair grader. Reply with one word.",
                    sleep=args.sleep)
                jud = "INCORRECT" not in verdict.upper() and "CORRECT" in verdict.upper()

            rec = {**item, "response": resp, "substring": sub,
                   "judge": jud, "correct": jud if jud is not None else sub}
            raw = getattr(backend, "last_raw", "")
            if raw and raw != resp:
                rec["raw_response"] = raw[:2000]   # keep for diagnosis
            records.append(rec)
            # 'err' not 'miss': an API failure is not a wrong answer, and
            # showing it as one makes a working model look broken.
            mark = "err " if errored else ("OK  " if rec["correct"] else "miss")
            print("  %3d/%d  %-24s %s" % (n, len(items), item["id"], mark),
                  flush=True)

            # Circuit breaker, checked AFTER the record is stored so nothing
            # is lost. A run where everything errors is not a score of 0% —
            # it's a broken setup, and grinding through 300 items to say so
            # wastes time and produces a misleading results file.
            if consecutive_errors >= 5:
                raise PermanentError(
                    "%d consecutive failures, last was:\n  %s"
                    % (consecutive_errors, resp[10:]))

            if n % 10 == 0:
                done_n = n - len(done)
                rate = done_n / max(1e-9, time.time() - t0)
                left = (len(items) - n) / rate if rate else 0
                print("      [%.1f items/s, ~%d min remaining]" % (rate, left / 60),
                      flush=True)
                save(records)

    except KeyboardInterrupt:
        save(records)
        answered = sum(1 for r in records if not is_error(r))
        print("\n\nStopped. %d answered items saved to %s\n"
              "Resume with the same command plus --resume\n" % (answered, out),
              file=sys.stderr)
        sys.exit(130)
    except PermanentError as e:
        save(records)
        answered = sum(1 for r in records if not is_error(r))
        msg = str(e)
        print("\nSTOPPED after %d items (%d answered and saved).\n\n  %s\n"
              % (len(records), answered, msg), file=sys.stderr)
        if "reasoning-only" in msg:
            print("This model spends its whole token budget thinking and never\n"
                  "answers. Either give it room, or use a model that doesn't\n"
                  "reason:\n"
                  "    ollama pull gemma3:4b       # no thinking mode at all\n"
                  "    python run_eval.py --model gemma3:4b \\\n"
                  "        --base-url http://localhost:11434/v1 --api-key ollama \\\n"
                  "        --data data/kk_grammar_gen.jsonl --max-tokens 64\n",
                  file=sys.stderr)
        elif "quota" in msg.lower():
            print("Free daily quota is used up; it resets on Google's schedule\n"
                  "(midnight US Pacific). Come back and re-run with --resume,\n"
                  "or switch to a local model with no quota at all.\n",
                  file=sys.stderr)
        else:
            print("Likely causes:\n"
                  "  * wrong --model name  -> --provider gemini --list-models\n"
                  "  * Google key starting 'AQ.' -> needs --provider gemini\n"
                  "  * Ollama not running  -> open the Ollama app\n"
                  "  * wrong --base-url, or no internet\n"
                  "\nRe-run with --resume to continue where you stopped.\n",
                  file=sys.stderr)
        sys.exit(2)

    score = report(records, args.model, "correct")
    save(records, score)
    print("Saved -> %s" % out)


if __name__ == "__main__":
    main()
