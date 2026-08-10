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
