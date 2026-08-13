# kaz-eval

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21921339.svg)](https://doi.org/10.5281/zenodo.21921339)

A generative benchmark for Kazakh nominal morphology, and the finding that
small language models know more Kazakh morphology than they can be asked to
demonstrate **in Kazakh**.

## The result

`gemma3:4b`, identical items, identical Kazakh gold answers, only the language
of the instruction varies:

| Instruction language | Accuracy |
|---|---:|
| Kazakh | 16.3% |
| Russian | 48.8% |
| English | 52.0% |

Noise floor is 2.7 points, measured over three independent item samples.

Adding **one** in-context example takes the Kazakh condition to 54.7%; five
take it to 74.7%, eliminating the gap entirely. The morphological knowledge was
there all along. The instruction could not reach it.

The effect also vanishes with scale: `gemma-4-31b-it` scores 98.7% under Kazakh
instructions, with one genuine morphological error in 300 items.

## Why this benchmark exists

Existing Kazakh benchmarks are multiple-choice. A model can score well on them
without ever producing a Kazakh word form, so they cannot separate *knowing*
Kazakh grammar from *being able to apply it*.

Here, gold answers are **computed from phonological rules** rather than
annotated by hand. Kazakh suffix selection depends on vowel harmony (the
front/back quality of the stem's last vowel) and consonant assimilation (the
stem-final segment selects the suffix onset). Encoding those rules means:

- items are reproducible from a seed and free to extend
- there is no annotator disagreement
- results can be conditioned on the properties that determine the answer --
  harmony class, stem-final sound, individual allomorph

## Quickstart

No dependencies beyond the Python standard library.

    python3 kaz_morph.py --selftest
    python3 kaz_morph.py --generate 300 --seed 7 > data/kk.jsonl
    python3 ru_prompts.py data/kk.jsonl data/ru.jsonl
    python3 en_prompts.py data/kk.jsonl data/en.jsonl

    python3 run_eval.py --model gemma3:4b \
        --base-url http://localhost:11434/v1 --api-key ollama \
        --data data/kk.jsonl --max-tokens 64

    python3 analyze.py results/gemma3-4b.json
    python3 summary.py

API-served models need `--max-tokens 1500`: reasoning tokens count against the
output budget and silently produce empty completions at smaller values.

## Coverage

Eight categories -- plural, six cases (genitive, dative, accusative, locative,
ablative, instrumental), third-person possessive -- over 50 regular noun stems
spanning both harmony classes and all six stem-final sound classes. 400 unique
items; runs sample 300.

Syncopating stems are excluded because their forms are not rule-derivable, so
the set slightly understates real difficulty.

## Files

| File | Purpose |
|---|---|
| `kaz_morph.py` | item generator; `--selftest` checks 54 hand-verified forms |
| `ru_prompts.py`, `en_prompts.py` | instruction-language conditions, ids/answers preserved |
| `fewshot.py` | prepend k worked examples in the item's own language |
| `run_eval.py` | run a model over a JSONL item set |
| `analyze.py` | breakdown by suffix, vowel harmony, stem-final sound |
| `summary.py`, `grid.py`, `shots.py`, `seedvar.py` | comparison tables |
| `PAPER.md` | full write-up, including five methodological findings |

## Known limitations

Nominal morphology only -- no verbs, no syntax, no fluency. Genitive is
reported with a caveat: the Kazakh genitive resists isolated elicitation
because the construction that hosts it (Type II izafet) takes a bare
possessor. Three gold answers collide with words in the Kazakh instruction
template. See `PAPER.md` Sections 6 and 8.

## Citation

```bibtex
@software{tuganbayev_kazeval_2026,
  author    = {Tuganbayev, Alikhan},
  title     = {kaz-eval: a generative benchmark for Kazakh nominal morphology},
  year      = {2026},
  publisher = {Zenodo},
  version   = {v1.1},
  doi       = {10.5281/zenodo.21921339},
  url       = {https://doi.org/10.5281/zenodo.21921339}
}
```

## Author

Alikhan Tuganbayev

## License

MIT. See `LICENSE`.
