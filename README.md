# Copy preflight

A small, opinionated linter for obvious copy problems. It catches stale-sounding phrases, long social paragraphs, unsupported checkable claims, missing visual review, and an optional configured LinkedIn topic boundary. It does **not** detect whether AI wrote something or promise to remove all bad writing. A zero-issue score is still `human_review`, never permission to publish.

**v0.2 adds grammar/cadence warnings** after a short post passed v0.1 but its author still called it AI-sounding. The exact rejected draft is a regression test: a teaser ending in "one test:", a staged question, and an "If ..., it's ..." verdict. Vocab and pattern flags describe the text, not who wrote it.

## Run

Python 3.9+; no third-party packages.

```bash
printf '%s\n' 'Leverage our revolutionary solution.' | python3 slopcheck.py --channel copy
printf '%s\n' 'Pretty photos do not get you booked. A clear Book button does.' | python3 slopcheck.py --channel x
python3 -m unittest -v
```

The CLI accepts `--input draft.txt`, `--channel copy|x|linkedin|instagram`, `--visual visual.json`, and `--evidence evidence.json`. It prints JSON with a score, blocked/review status, issue codes, spans and suggested fixes. The score is a surface-problem heuristic, not a probability or a quality guarantee. See `spec.json` for thresholds and vocabulary. Change those before applying it to another person's voice.

A social post needs a separate visual record such as `{"inspected":true,"real_asset":true,"privacy_checked":true}`. Those flags document a human check; the program cannot inspect the image itself. A claim-specific record looks like:

```json
[{"claim":"30%","source":"https://example.org/original-receipt","note":"The source actually states this figure","checked":true}]
```

A URL by itself never clears a claim flag. These records are attestations by the caller, not proof verified by the software. Keyword detection misses many factual claims and can flag innocent numbers. Publication still requires checking the original source, audience, image pixels, privacy, platform state and local context.

## What is checked

- Hard words or template phrases trigger a block; softer clichés trigger review.
- Rhetorical teaser + question and question + if/verdict are blocked. False contrasts, em-dash pivots, "here's the thing" openers, short if/then morals, and repeated three-line beats prompt review. Regexes are intentionally narrow and will miss variants or flag intentional style.
- Social copy over channel targets, sentences over 24 words, and uninterrupted lines over 32 words are flagged.
- Numbers and a narrow set of claim verbs require a claim-specific checked source record.
- A social post without a real, inspected, privacy-checked visual blocks.
- Set `linkedin_blocked_terms` in `spec.json` for your own audience restrictions. The public default is empty.

Not covered: images or layouts, exact truth of sources, linked pages, post timing, cross-channel audience judgment, duplicate posts, originality, platform labels, or publication. Never feed private messages or customer data into a public test fixture.

## Example from a real rejected pattern, sanitized

Bad: a long, unbroken social paragraph about what an agent does, without a visual. The linter flags `WALL_OF_TEXT` and `VISUAL_UNVERIFIED`.

Better draft: "Show me who it contacted.\n\nShow me what it couldn't finish." Still blocked until an actual product image is inspected and the claim is checked. Shorter is not automatically good.

## Development

Run `python3 -m unittest -v`. The 14-test suite includes the exact owner-rejected v0.1 false negative. It guards against obvious regressions, not writing quality. Candidate changes should also be blind-reviewed on a consented, private set of good/bad examples by a prospect, skeptical copywriter, skeptical buyer, nontechnical reader, and growth reviewer. Don't train or publish those examples without permission. Add false-positive and false-negative tests as you learn.

License: MIT. Contributions should include a failing test and explain why the changed rule helps rather than merely gaming the score.
