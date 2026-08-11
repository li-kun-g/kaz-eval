# kaz-eval — state as of 2026-08-10

## Headline
gemma3:4b on 300 Kazakh nominal-morphology items, identical gold answers,
only the INSTRUCTION LANGUAGE differs:

    Kazakh prompts   49/300 = 16.3%
    Russian prompts 145/300 = 48.3%

Excluding genitive (broken item type, see below):

    Kazakh  32/259 = 12.4%   ->   Russian 145/259 = 56.0%   (4.5x)

Conclusion: most of gemma3:4b's apparent Kazakh incompetence is an
instruction-following failure, not missing morphology. Points at Kazakh
instruction tuning rather than continued pretraining.

## Per category (KK -> RU)
    plural  63.6 -> 60.6      loc     7.5 -> 75.0
    gen     41.5 ->  0.0*     abl     3.7 -> 59.3
    dat      2.4 -> 41.5      ins    12.5 -> 75.0
    acc      0.0 -> 25.0      poss3   2.6 -> 57.9

## Secondary findings
- Genitive is NOT elicitable in isolation. Kazakh ilik septik only occurs in
  izafet (balanyn kitaby), so a bare genitive is not a well-formed answer.
  Two different Russian glosses both failed (0/41, then 2/41); the model
  returns the possessed form instead. The item format is wrong, not the gloss.
- Prompt sensitivity is large: one mistranslated case label moved a category
  by 41 points. This eval measures prompts as much as models.
- Once the instruction bottleneck lifts, real phonology appears:
  front-vowel stems 42.2% vs back-vowel 52.2%; dative defaults to -ga
  (66.7%) and fails -qa 25.0% / -ke 20.0%.
- Turkish-script leakage (Mektepler, Latin schwa) appeared ONLY under Kazakh
  prompts. It is a symptom of not parsing the request, not a knowledge gap.

## Files
    kaz_morph.py    generator, --selftest checks 50 hand-verified forms
    ru_prompts.py   rewrites question text into Russian, ids/answers identical
    fix_gen.py      genitive-only variant (v2 gloss, still broken)
    analyze.py      breakdown by suffix / harmony / stem-final sound
    data/kk_grammar_gen.jsonl   300 items, Kazakh prompts
    data/kk_grammar_ru.jsonl    300 items, Russian prompts
    results/gemma3-4b-kk.json / -ru.json / -gen-v2.json

## Next (decided, not started)
Second model through the identical pair, to see if the gradient replicates.
One model is an anecdote.

    ollama pull qwen2.5:3b
    python3 run_eval.py --model qwen2.5:3b --base-url http://localhost:11434/v1 \
        --api-key ollama --data data/kk_grammar_gen.jsonl --max-tokens 64 && \
    mv results/qwen2.5-3b.json results/qwen2.5-3b-kk.json && \
    python3 run_eval.py --model qwen2.5:3b --base-url http://localhost:11434/v1 \
        --api-key ollama --data data/kk_grammar_ru.jsonl --max-tokens 64 && \
    mv results/qwen2.5-3b.json results/qwen2.5-3b-ru.json && \
    python3 analyze.py results/qwen2.5-3b-kk.json results/qwen2.5-3b-ru.json

Disk was tight today (~15GB free). Check `df -h /` before pulling.

---

## Session 2 update

Added: gemma-4-31b-it ceiling run, qwen2.5:3b pair, truncation control,
izafet genitive experiment, FINDINGS.md.

Key result — instruction-language gap is a SMALL-MODEL pathology:

    qwen2.5:3b      KK  4.3%   RU 21.0%   (+16.7)
    gemma3:4b       KK 16.3%   RU 48.3%   (+32.0)
    gemma-4-31b-it  KK 98.5%   RU 97.6%   ( -0.9)   <- gap vanishes at scale

31B figures are over answered items; 19/150 and 27/150 responses came back
blank. run_eval.py has been patched so blanks no longer count as wrong.

Landscape: KazMMLU (MBZUAI, ACL 2025) is the incumbent Kazakh benchmark but
is 100% multiple-choice and never mentions morphology. Their paper says the
Kazakh/Russian gap "could be due to training data, language complexity, or
tokenization" and does not test which. That is the opening. Positioning
paragraph is drafted in FINDINGS.md discussion.

### Open right now
1. Izafet genitive FAILED at 4B: 0/50 in both languages, vs 41.5% for bare
   genitive under Kazakh prompts. Likely cause: my izafet prompt is a longer,
   more complex instruction, and instruction complexity is the binding
   constraint at 4B. UNRESOLVED — decide with the 31B run below.
2. summary.py not yet created on this machine (heredoc pending from chat).
3. Seed-variance run (seeds 7/8/9, gemma3:4b) not started. ~19 min.

### Next command (needs: export GEMINI_KEY="...")
    python3 run_eval.py --provider gemini --model gemma-4-31b-it \
        --api-key "$GEMINI_KEY" --data data/kk_izafet.jsonl \
        --max-tokens 256 --no-think && \
    mv results/gemma-4-31b-it.json results/gemma-4-31b-it-izafet-kk.json

If 31B scores high on izafet -> item type is sound, 4B zero is instruction
complexity. If 31B also fails -> drop genitive from the benchmark.

---

## Session 3 update

### CORRECTED ceiling numbers (the old ones were contaminated)
Root cause found: gemma-4-31b-it does hidden reasoning that counts against
maxOutputTokens. At --max-tokens 256, ~208 tokens went to thinking and the
answer was never emitted -> blank responses scored as wrong. --no-think does
NOT suppress it. Fix: --max-tokens 1500.

Clean numbers, ZERO blanks:

    qwen2.5:3b       KK   4.3%   RU  21.0%   (+16.7)
    gemma3:4b        KK  16.3%   RU  48.3%   (+32.0)
    gemma-4-31b-it   KK  98.7%   RU 100.0%   ( +1.3)

Only 2 errors in 300 at 31B, and only one is morphological:
  ul  -> "Olar" (lexical slip, wrong word entirely)
  soz -> "sozning" instead of "sozdin" -- wrong assimilation allomorph
         after z. Harmony was correct. This is THE single genuine
         morphological error at 31B.

### Izafet genitive: half-rescued, then complicated
31B scores 46/49 on izafet items. All three errors are bet/bas/is -- exactly
the nouns where a Type II compound reading is natural (bet sureti = portrait).

IMPORTANT LINGUISTIC CORRECTION: Kazakh izafet Type II (bala kitaby) takes a
BARE possessor. My frame "___ sureti" is a Type II slot, so the bare stem is
arguably the correct answer and my gold demanding genitive is wrong for these.
Type III (balanyn kitaby) requires a definite possessor, which the prompt does
not supply.

=> Three genitive elicitation attempts, three different failure modes:
   kogo/chego pulled to ablative; prinadlezhnosti pulled to possessive;
   izafet frame underspecified for definiteness.
   DECISION: report seven categories. Document genitive as a category this
   methodology cannot cleanly measure, with the three failures as evidence.
   That is a methodological contribution, not a gap. Do not attempt a fourth.

### Done this session
- run_eval.py patched: blanks are errors, not wrong answers
- kaz_morph.py v2: --tasks flag, gen_izafet, selftest 54/54
  (default 300/seed 7 still byte-identical to original)
- ru_prompts.py v2: takes paths, handles gen_izafet
- seeds 7/8/9 run for gemma3:4b Kazakh prompts -- NOT YET ANALYZED

### Tomorrow, in order
1. python3 seedvar.py            <- analyze the seed runs, get the noise floor
2. Update FINDINGS.md: corrected 31B numbers, noise floor, genitive decision,
   the reasoning-token bug as a fifth methodological finding
3. Choose direction: extend to verbs / write the paper / email MBZUAI

Note: FINDINGS.md still contains the OLD contaminated 86.0/80.0 and 98.5/97.6
figures. Replace with 98.7/100.0.

## Noise floor (measured, seeds 7/8/9, gemma3:4b, Kazakh prompts)

    seed 7: 16.3%   seed 8: 18.0%   seed 9: 15.3%
    mean 16.6%   sd 1.35   range 2.7 points

Per-category range across the three item samples:

    plural 12.0 | gen 3.1 | loc 3.0 | dat 2.6
    ins     2.5 | abl 1.0 | poss3 0.1 | acc 0.0

READING:
- Headline +32.0 gap is ~12x the noise. Safe.
- dat/acc/loc/abl/ins/poss3 gaps all far outside their ranges. Safe.
- PLURAL is NOT safe: the -3.0 KK-vs-RU difference sits inside a 12-point
  noise range. Drop any claim about plural being "unchanged".
- Variance is near zero where the model is floored (acc 0.0, poss3 0.1) and
  largest where it is mid-range (plural ~65%). Binomial variance peaks at
  p=0.5, so partially-competent categories need the most data. Worth saying
  in a methods section.
- Seed 7 reproduced the original run item-for-item. Determinism confirmed.

## Next session
FINDINGS.md does NOT exist on disk (the heredoc paste hit a terminal length
limit and was aborted cleanly). Rebuild it in 3-4 smaller chunks. Content
needed: corrected 31B numbers (98.7 KK / 100.0 RU, zero blanks), the noise
floor above, the genitive decision (7 categories, genitive documented as
unmeasurable), and the reasoning-token bug as finding 3.
