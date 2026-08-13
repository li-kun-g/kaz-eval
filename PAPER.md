# What Small Models Know About Kazakh Morphology and Cannot Be Asked

Alikhan Tuganbayev

## Abstract

Multiple-choice benchmarks report that language models underperform in Kazakh
relative to Russian, but cannot say why: a model can answer them without ever
producing a Kazakh word form. We introduce a generative benchmark of Kazakh
nominal inflection covering eight morphological categories over fifty regular
noun stems, with gold answers computed from vowel-harmony and
consonant-assimilation rules rather than annotated by hand. Holding items and
gold answers byte-identical while varying only the language of the instruction,
we find that small models are limited by instruction comprehension rather than
by morphological knowledge. gemma3-4b scores 16.3% under Kazakh instructions
against 48.8% in Russian and 52.0% in English, with a noise floor of 2.7
points; qwen2.5-3b scores 4.3% and 21.0%. The deficit is not uniform:
categories whose Kazakh grammatical terminology is common show little or no
penalty, while those with more specialised terminology fall to zero. A single
in-context example raises Kazakh-instructed accuracy to 54.7% and five raise it
to 74.7%, eliminating the gap, with gains concentrated precisely in the
categories that had failed -- the knowledge was present throughout and the
instruction could not reach it. This reconciles our findings with prior work
reporting a 1-5 point instruction-language penalty for Turkish and Finnish
under few-shot prompting: demonstrations substitute for instruction
comprehension and therefore mask the effect. The gap also vanishes with scale,
gemma-4-31b reaching 98.7% and 100.0% with one genuine morphological error in
300 items. We further report five methodological findings for cross-lingual
generative evaluation, including a translated case label that moved one
category by 41 points and was fully rescued by examples, a morpheme that
resists isolated elicitation on grammatical grounds, and hidden reasoning
tokens that silently consume the output budget and are scored as errors.

## 1. Introduction

Kazakh is spoken by roughly fourteen million people and is an official language
of a country of twenty million, yet remains among the languages for which large
language models are least reliable. It is also agglutinative: nominal stems take
suffixes whose surface form is determined jointly by vowel harmony, which
propagates the front/back quality of the last stem vowel, and by consonant
assimilation, which selects the suffix onset according to the voicing and manner
of the stem-final segment. A model that has memorised frequent word forms and a
model that has acquired the underlying rules are indistinguishable on any
benchmark that does not require the model to *produce* a form it may never have
seen.

Existing Kazakh benchmarks do not require this. KazMMLU (Togmanov et al., 2025),
the largest and most widely used, comprises 23,000 multiple-choice questions; a
model can score well on all of them without emitting a single Kazakh word form.
Its authors observe that models perform better in Russian than in Kazakh and
attribute the gap to "differences in training data availability, language
complexity, or tokenization differences," without distinguishing between them.
Multiple-choice evaluation cannot make that distinction: it conflates knowing
something with being able to say it.

We introduce a generative benchmark for Kazakh nominal morphology in which gold
answers are derived from phonological rules rather than annotated by hand,
making the item set reproducible from a seed, cheap to extend, and free of
annotator disagreement. Each item presents a citation-form noun and a target
morphological category and requires the model to produce the inflected form.
Because the gold answer is computed, the analysis can be conditioned on the
linguistic properties that determine it -- harmony class, stem-final sound, and
the specific allomorph -- so that we report where a model fails rather than only
how often.

Our central experiment holds items and gold answers byte-identical while varying
only the language of the instruction. Small models prove limited by instruction
comprehension rather than morphological knowledge. That English performs on par
with Russian rules out an explanation grounded in Kazakhstan's bilingual
situation: the effect is instruction comprehension in general, not transfer from
a contact language. A single in-context example recovers most of the deficit and five
eliminate it, showing that the knowledge was present and the instruction
could not reach it (Section 5.7). Underneath that parity, however, the choice of instruction
language shifts individual categories by 20-30 points in opposite directions,
which we discuss in Section 6. The morphology is largely present in models that
appear, when addressed in Kazakh, not to have it.

## 2. Related work

**Kazakh benchmarks.** KazMMLU (Togmanov et al., 2025) is the reference point:
23,000 bilingual multiple-choice questions drawn from educational materials
across STEM, humanities and social sciences. ISSAI's KAZ-LLM suite [CITE]
provides evaluation scripts and datasets alongside a Kazakh-centric model.
KazQAD [CITE] targets question answering and retrieval, KazSim [CITE] text
simplification, and Qorgau [CITE] safety in the Kazakh-Russian bilingual
setting. All are task-level evaluations; none targets morphological generation,
and none reports results conditioned on phonological properties of the target
form.

**Morphological evaluation.** The SIGMORPHON-UniMorph shared tasks have treated
morphological inflection as a supervised problem for a decade, most recently
covering 26 languages from 9 families with lemma-disjoint splits designed to
test generalisation to unseen lemmas (SIGMORPHON-UniMorph 2023 Shared Task 0).
Our item format -- lemma plus target features, inflected form as output --
follows that tradition, but evaluates instruction-following models zero-shot
rather than trained inflection systems.

Closest to the present work, "Evaluating Morphological Compositional
Generalization in Large Language Models" (NAACL 2025; arXiv:2410.12656)
evaluates instruction-tuned multilingual models on Turkish and Finnish, treating
morphemes as compositional primitives and testing productivity and systematicity
over novel roots. It reports sharp degradation as morphological complexity rises
and a lack of systematicity relative to humans. We differ in three respects: the
language is Kazakh; the instruction language is manipulated while the task and
gold answers are held fixed, which that work does not do; and our focus is the
small-model regime, where the effect we report is largest, rather than frontier
models.

"Evaluating Metalinguistic Knowledge in Large Language Models across the World's
Languages" (arXiv:2602.02182) converts WALS features into multiple-choice
questions across 2,660 languages and finds metalinguistic knowledge to be
fragmented and predicted mainly by digital resource availability rather than by
genealogical or geographic factors. That is consistent with our interpretation
in Section 5.3, though it measures knowledge *about* languages rather than the
ability to act on grammatical instructions *in* a language, and is itself
multiple-choice.

[TO VERIFY BEFORE SUBMISSION: arXiv:2411.14198 "Why do language models perform
worse for morphologically complex languages?"; arXiv:2511.01380 "Confounding
Factors in Relating Model Performance to Morphology"; MultiBLiMP 1.0
(morphosyntactic minimal pairs, 101 languages). Titles located but contents not
read. Also fill exact author lists and page numbers for all citations above.]

**Prompt-language effects.** Cross-lingual prompting studies have reported that
instructing a multilingual model in a high-resource language can outperform
instructing it in the target language [CITE]. Our contribution is to isolate
this effect on a task whose *output* is fixed in the low-resource language
regardless of instruction language, so that any difference is attributable to
instruction comprehension rather than to output-language fluency.

## 3. The benchmark

### 3.1 Item construction

Each item pairs a citation-form Kazakh noun with a target morphological
category and requires the inflected form as output. Eight categories are
covered: plural, six cases (genitive, dative, accusative, locative, ablative,
instrumental) and third-person possessive.

Gold answers are computed, not annotated. Suffix selection in Kazakh is
determined by two independent factors. Vowel harmony assigns the suffix vowel
according to the front/back quality of the last full vowel of the stem, so
`үй` takes `-лер` while `тау` takes `-лар`. Consonant assimilation selects the
suffix onset according to the stem-final segment, partitioning consonants into
five classes: vowels and р/у/й take л-initial plural suffixes; л, м, н, ң, ж, з
take д-initial; voiceless segments take т-initial. Distinct partitions apply to
each case. A third rule voices stem-final п, қ, к before vowel-initial
suffixes, so `кітап` becomes `кітабы` and `сабақ` becomes `сабағы` under
third-person possessive.

Encoding these rules as tables makes the item set reproducible from a random
seed, free to extend to new stems, and free of annotator disagreement. It also
permits conditioning the analysis on the properties that determine the answer,
so that results can be reported by harmony class, by stem-final sound class,
and by individual allomorph rather than only by category.

### 3.2 Lexicon and exclusions

Fifty regular noun stems are used, thirty back-harmonic and twenty
front-harmonic, spanning all six stem-final sound classes. Stems that undergo
syncope under suffixation -- `халық` to `халқы`, `орын` to `орны`, `ауыз` to
`аузы` -- are deliberately excluded, since their surface forms are not derivable
from the rules above. The benchmark therefore slightly understates the
difficulty of real Kazakh.

Fifty stems and eight categories yield 400 unique items, from which a run
samples 300 without replacement.

### 3.3 Validation

The rule tables are checked against 54 hand-verified forms before every
generation; the generator refuses to emit items if any check fails. This guards
against the failure mode in which a systematic error in the tables silently
produces hundreds of incorrect gold answers.

### 3.4 Grading

Responses are graded by substring match against an accept list after removal of
words echoed from the question. Echo removal is necessary because a model that
merely repeats the prompt would otherwise score correct whenever the prompt
contains a substring of the answer. Blank completions are treated as
non-answers and excluded from the denominator rather than scored as errors
(Section 7).

## 4. Experimental setup

### 4.1 Conditions

The instruction-language manipulation rewrites only the `question` field of
each item. Identifiers, gold answers and accept lists are preserved
byte-for-byte, so conditions are paired item-for-item and any difference is
attributable to the instruction alone. In all conditions the required output is
Kazakh.

Kazakh instructions use standard school grammatical terminology
(`табыс септігінде (кімді? нені?)`). Russian and English instructions use the
corresponding case names in those languages together with their conventional
interrogative cues.

### 4.2 Models

Three models are evaluated: qwen2.5-3b and gemma3-4b served locally through
Ollama, and gemma-4-31b-it accessed through a hosted API. gemini-3.6-flash was
additionally used as a ceiling check on a subset. Decoding is greedy; repeated
runs on identical items reproduce identical outputs.

Local models were given a 64-token budget, sufficient for single-word answers;
API models required 1500 tokens for reasons discussed in Section 7.

### 4.3 Noise floor

Because items are sampled from a larger pool, run-to-run variation is
non-zero. We estimate it by drawing three independent 300-item samples (seeds
7, 8, 9) and evaluating the same model under the same condition. All reported
differences are compared against the observed range for the relevant category.

## 5. Results

### 5.1 Scale

| Model | Params | Kazakh | Russian | English |
|---|---:|---:|---:|---:|
| qwen2.5-3b | 3B | 4.3 | 21.0 | -- |
| gemma3-4b | 4B | 16.6 +-1.3 | 48.8 +-1.0 | 52.0 +-1.3 |
| gemma-4-31b-it | 31B | 98.7 | 100.0 | -- |

gemma3-4b figures are means over three independent item samples, with half the
observed range. Others are single runs of 300 items (3B) and 150 items (31B).

Two small models show the same pattern: a large deficit under Kazakh
instructions that a high-resource instruction language largely removes. At 31B
the deficit is absent. Note that gemma3-4b and gemma-4-31b-it belong to
different model generations, so the comparison confounds capacity with a
generation of training improvements; a within-generation control at 12B was
attempted but not completed for reasons of local disk (Section 8).

### 5.2 Instruction language by category

The overall difference between Russian and English is 3.2 points, marginally
outside the 2.7-point noise band. Beneath that near-parity, individual
categories diverge by an order of magnitude more, in both directions:

| Category | Kazakh | Russian | English | difference |
|---|---:|---:|---:|---:|
| plural | 68.7 +-6.0 | 58.9 +-2.0 | 68.0 +-1.5 | EN +9.1 |
| genitive | 42.2 +-1.5 | 1.8 +-1.5 | 28.2 +-3.2 | EN +26.4 |
| dative | 1.7 +-1.3 | 33.6 +-6.8 | 48.4 +-5.8 | EN +14.8 |
| accusative | 0.0 +-0.0 | 31.0 +-5.4 | 62.9 +-3.3 | EN +31.9 |
| locative | 9.2 +-1.5 | 76.7 +-2.0 | 51.6 +-2.4 | RU +25.1 |
| ablative | 3.1 +-0.5 | 57.9 +-1.3 | 40.8 +-5.9 | RU +17.1 |
| instrumental | 11.0 +-1.2 | 74.6 +-4.5 | 53.4 +-2.6 | RU +21.2 |
| possessive-3 | 2.6 +-0.1 | 56.4 +-1.4 | 62.4 +-2.1 | EN +6.0 |

Russian instructions are substantially better for the oblique cases -- locative,
instrumental, ablative -- while English instructions are substantially better for
accusative and genitive. Russian lexicalises an instrumental and a
locative/prepositional case; English has no case morphology and its case terms
are purely metalinguistic. Whether the interaction reflects that difference in
grammatical inventory, or simply uneven quality across our own glosses, is not
resolvable with the present design (Section 8).

### 5.3 The Kazakh penalty is category-specific

The deficit under Kazakh instructions is not uniform. For plural, Kazakh
instructions perform as well as English (68.7 against 68.0). For genitive they
outperform both alternatives (42.2 against 28.2 and 1.8). For accusative and
dative they collapse to near zero.

The categories that survive Kazakh prompting are those whose Kazakh
grammatical terms -- `көпше түрі`, `ілік септік` -- are basic school vocabulary;
those that fail use more specialised terminology. This suggests that the
bottleneck is coverage of Kazakh metalinguistic vocabulary rather than an
inability to process Kazakh instructions in general, and predicts that term
frequency in Kazakh corpora should predict which categories survive. We do not
test that prediction here.

### 5.4 Neighbour-language interference

Under Kazakh instructions, both small models produce forms drawn from a
better-resourced Turkic relative, and they draw on different ones. gemma3-4b
produces `Мектеpler` for `мектептер`, grafting the Turkish plural `-ler` in
Latin script onto a Cyrillic stem, and substitutes Latin `ə` for Cyrillic `ә`.
qwen2.5-3b produces Kyrgyz morphology (`айтып берет` where Kazakh requires
`айтып береді`) and Kyrgyz lexical items.

This interference is largely absent under Russian and English instructions,
which supports reading it as a symptom of failed instruction parsing rather
than of a corrupted Kazakh lexicon.

### 5.5 Phonological conditioning

Where models are above the floor, back-harmonic stems outperform front-harmonic
ones: 52.2 against 42.2 for gemma3-4b under Russian instructions, 25.5 against
13.8 for qwen2.5-3b. At 31B both classes reach 100%.

qwen2.5-3b scores 0/40 on instrumental under both Kazakh and Russian
instructions -- the `-мен/-бен/-пен` paradigm appears to be absent from the model
rather than merely unreachable. gemma3-4b handles instrumental at 74.6 under
Russian. Two models of comparable size therefore fail on different categories,
and an intervention targeting either would need to be built against measured
per-model gaps.

### 5.6 Error profile at ceiling

gemma-4-31b-it makes two errors in 300 items. One is lexical: `ұл` returns
`Олар` ("they"). The other is the single genuine morphological error observed
at this scale: `сөз` returns `сөзнің` where Kazakh requires `сөздің`, applying
the post-nasal allomorph after a fricative. Vowel harmony is correct;
assimilation is not. All other cuts of the data -- both harmony classes, all six
stem-final sound classes, every allomorph -- are at 100%.

## 6. Methodological findings

We report five issues encountered in building this evaluation. Each cost
substantial time to diagnose and each generalises beyond Kazakh.

**6.1 A translated case label moved one category by 41 points.** We first
glossed Kazakh ілік септік as Russian `родительный падеж (кого? чего?)`.
Russian's `кого?/чего?` overlaps with the accusative and with negation
constructions and does not signal possession; the model was pulled toward
ablative and instrumental forms (`шаң` returning `Шаңмен`, `түн` returning
`Түннен`). Genitive fell from 42.2 under Kazakh instructions to 1.8 under
Russian. All six allomorphs scored near zero uniformly -- the signature of a
category never identified, as opposed to a phonological error, which would
fail some allomorphs and spare others. A cross-lingual evaluation measures its
own translations as much as it measures the model.

**6.2 The Kazakh genitive resists isolated elicitation.** Three attempts failed
in three distinct ways. The `кого? чего?` gloss pulled toward oblique cases.
A revised `родительный падеж принадлежности (чей? чьё?)` pulled toward the
possessed form (`шаң` returning `Оның шаңы`, `дос` returning `Досының`). An
izafet frame (`___ суреті`) scored zero at 4B but 93.9 at 31B, and its residual
errors at 31B were confined to `бет`, `бас` and `іс` -- exactly the nouns that
form natural compounds.

The explanation is grammatical. Kazakh izafet Type II (`бала кітабы`) takes a
bare possessor; Type III (`баланың кітабы`) requires a definite possessor that
an isolated prompt does not supply. The frame is a Type II slot, so the bare
stem is a legitimate answer and our genitive gold is wrong for those items.
The construction that hosts the genitive does not require it. We therefore
report the genitive with this caveat rather than treating its scores as a clean
measure of morphological competence.

**6.3 Hidden reasoning tokens consume the output budget silently.** The hosted
gemma-4-31b-it performs internal reasoning that counts against
`maxOutputTokens`. At a 256-token budget, roughly 208 tokens went to reasoning
and the answer was never emitted; the API returned an empty completion.
Symptoms were 12-48% blank responses varying between runs and answers truncated
mid-word. Requesting suppression of reasoning did not prevent it. Raising the
budget to 1500 tokens eliminated blanks entirely and moved the measured score
from 86.0 to 98.7. Any API-based evaluation of a reasoning-capable model needs
a budget far above the visible answer length and an explicit blank-rate check.

**6.4 Blank responses were being scored as wrong answers.** Our harness
initially treated only explicit API errors as errors, so empty completions
counted against accuracy. A non-answer is not a wrong answer; it belongs
outside the denominator, and it should be retried on resumption.

**6.5 Generation-length truncation was ruled out rather than assumed.**
qwen2.5-3b produces long meta-commentary under Kazakh instructions and hit its
64-token ceiling. Re-running sixty items at 256 tokens produced exactly the
same four correct answers while throughput fell from 0.6 to 0.4 items per
second: the model generated more text and used it to elaborate rather than to
answer. The low score is genuine.

## 7. Validity

gemini-3.6-flash answered the first seven Kazakh-instruction items correctly
before quota exhaustion, including the two instrumental items on which
qwen2.5-3b fails forty times out of forty. gemma-4-31b-it reached 98.7% with
zero blank responses. The items are well-formed and answerable in Kazakh; low
scores at small scale reflect model behaviour rather than a defective
instrument.

## 8. Limitations

The benchmark covers fifty regular noun stems and eight suffix categories. It
contains no verbs, no syntax, no irregular stems, and no measure of fluency or
translation quality; a model could score perfectly here and still write poor
Kazakh. Syncopating stems are excluded, so the set understates real difficulty.

Genitive results carry the caveat in 6.2. Plural differences between
instruction languages fall inside the noise floor and support no claim.

The category-by-instruction-language interaction in 5.2 admits two
explanations we cannot separate: the instruction language's own grammatical
inventory, or uneven quality across our glosses. Given 6.1, the second is a
live possibility. Distinguishing them requires multiple independent glosses per
category per language, which we leave to future work.

The scaling comparison spans two model generations. Error bars are available
for gemma3-4b only; other models were run once. The noise floor is estimated
from item sampling and does not capture decoding variance, which is nil under
greedy decoding, or variance across prompt phrasings, which 6.1 suggests is
large. Three models establish a trend, not a scaling law.

## 9. Conclusion

Small multilingual models know more Kazakh nominal morphology than they can be
asked to demonstrate in Kazakh. Instructing gemma3-4b in Russian or English
rather than Kazakh raises accuracy from 16.6 to roughly 50 on identical items
with identical Kazakh answers, and the deficit disappears entirely at 31B
parameters. The gap is not uniform across the paradigm: it is largest for
categories whose Kazakh grammatical terminology is least common, which locates
the bottleneck in metalinguistic vocabulary rather than in morphological
knowledge or in Kazakh processing as such.

For practitioners building Kazakh systems on small open-weight models, this
suggests that instruction tuning on Kazakh task descriptions is likely to
recover more capability per unit of compute than continued pretraining on
Kazakh text. For evaluation, it suggests that any multiple-choice benchmark
reporting a Kazakh-Russian gap is measuring a mixture of knowledge and
instruction comprehension, and cannot separate them by design.

## Availability

Code and item sets: https://github.com/li-kun-g/kaz-eval
Archived release: https://doi.org/10.5281/zenodo.21921339 All items are generated from a seed; the
generator validates its rule tables against hand-verified forms before emitting
anything.

### 5.7 In-context examples close the gap

The results above are zero-shot. Prior work on morphological evaluation in
agglutinative languages prompts with in-context examples, and reports only a
1-5 point penalty for instructing in the target language rather than English
(arXiv:2410.12656, Appendix A.1). We reconcile the two by varying the number of
examples on our own items.

| Category | KK 0-shot | KK 1-shot | KK 5-shot | RU 0-shot | RU 5-shot |
|---|---:|---:|---:|---:|---:|
| plural | 63.6 | 69.7 | 84.8 | 60.6 | 78.8 |
| genitive | 41.5 | 51.2 | 68.3 | 0.0 | 75.6 |
| dative | 2.4 | 70.7 | 80.5 | 41.5 | 63.4 |
| accusative | 0.0 | 22.5 | 67.5 | 25.0 | 72.5 |
| locative | 7.5 | 55.0 | 62.5 | 75.0 | 47.5 |
| ablative | 3.7 | 44.4 | 66.7 | 59.3 | 55.6 |
| instrumental | 12.5 | 70.0 | 87.5 | 75.0 | 85.0 |
| possessive-3 | 2.6 | 52.6 | 78.9 | 57.9 | 81.6 |
| **OVERALL** | **16.3** | **54.7** | **74.7** | **48.3** | **70.3** |

A single example raises Kazakh-instructed accuracy from 16.3 to 54.7. Five
examples raise it to 74.7, at which point it slightly exceeds the Russian
condition: the 32.0-point instruction-language gap becomes -4.3. Kazakh gains
58.3 points from examples while Russian gains 22.0.

The gains are not uniform, and their distribution supports the account in
Section 5.3. The categories that gain most from one example are exactly those
where Kazakh instructions failed: dative +68.3, instrumental +57.5, possessive
+50.0, locative +47.5, ablative +40.7. The two categories the model already
handled under Kazakh instructions gain least: plural +6.1 and genitive +9.7.
An example supplies what a grammatical term failed to convey -- which
transformation is intended -- and it is redundant where the term was already
understood.

The Russian genitive provides an internal check. Under our first Russian gloss
it scored 0.0 (Section 6.1); with five examples it reaches 75.6. The model's
genitive knowledge was intact throughout; a mistranslated case label concealed
it, and demonstrations bypass the label entirely.

**Implication for evaluation practice.** Few-shot prompting substitutes for
instruction comprehension and therefore masks instruction-language effects. A
benchmark that reports few-shot numbers is measuring something closer to
analogical pattern completion than to a model's ability to act on grammatical
instructions in the target language. Both are worth measuring, but they are
different capabilities, and reporting only the former will understate how
poorly a model serves users who write in that language.

Two caveats. With five same-category demonstrations the model observes most of
the allomorph inventory for that category, so the 5-shot condition is closer to
analogy than to rule application; the 1-shot figure is the more conservative
one. And the Russian condition loses ground on locative (75.0 to 47.5) and
ablative (59.3 to 55.6) under 5-shot prompting, which we do not currently
explain.
