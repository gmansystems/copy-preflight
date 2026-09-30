# Quality audit - September 30, 2026

## Verdict

v0.2.0 is not ready to hand to a stranger as a dependable slop checker. It is a small regex prototype with useful reminders. The code is readable and has no third-party Python dependencies, but its defaults create avoidable false alarms and its tests do not establish writing-quality performance.

The patch makes it reasonable to show as an **experimental phrase linter**, with its limits stated. It does not make it a reliable editorial gate.

## Method

Cloned public main and compared the v0.2.0 tag. Both pointed to `00264cf98d44271c4b5ea03370af9a77fa469028`. Ran its existing suite, tested ordinary sentences and invented promotional copy, then inspected source, input validation, configuration and CLI behavior. These are synthetic probes, not a blinded or representative benchmark. No precision/recall claims are warranted.

Source: https://github.com/gmansystems/copy-preflight
Release under audit: https://github.com/gmansystems/copy-preflight/releases/tag/v0.2.0

## Observed defects and fixes

| Probe or defect in v0.2.0 | Original result | Patch result |
| --- | --- | --- |
| "The operator restarted the pump." | Blocked as generic language | No issues |
| "Transform the coordinates before drawing the map." | Blocked | No issues |
| "Use Tab to navigate between fields." | Blocked | No issues |
| "I live near the station." | Unsupported-claim block | No issues |
| "Read the first line only." | Unsupported-claim block | No issues |
| "Our platform empowers teams and unlocks their potential." | 100, no issues | Vocabulary review |
| "Discover a world of possibilities. Take your business to the next level." | 100, no issues | Vocabulary review |
| "In an ever-evolving digital landscape, innovation is the key to success." | 100, no issues | Vocabulary review |
| Curly apostrophes in rejected question/if draft | Missed question/if rule | Matches that rule |
| Visual flags are the strings "false" | Accepted as checked | Input error |
| `visual_required: false` | Ignored | Honored |
| `python3 test_slopcheck.py` | Runs 7 of 14 tests | Runs all 14 in that file |
| Blocked CLI result | Always exits 0 | Still 0 by default; optional explicit gate exits 1 |
| Invalid JSON / wrong input shape | Traceback or loose acceptance | Error on stderr, exit 2 |
| Long paragraph split with single newline | Evades paragraph rule | Matched as one paragraph |
| Fragment spans with intervening blank lines | Truncated span | Full matched span |

The public lexicon now gives vocabulary warnings rather than automatic blocks. Common technical words were removed from the public defaults. A caller can still configure hard blocks. Claim matches are reminders, not unsupported-truth verdicts. This is a deliberate behavior change, not an accuracy measurement.

The patch adds local regression tests, an ignore file and a proposed CI workflow. The CI matrix has not been run on GitHub. Local tests cover the installed Python version only.

## What is genuinely weak

1. No independent evaluation. The existing suite mostly asserts that the patterns programmed into the tool match. Adding these probes improves regression coverage but does not fix that evidence gap.
2. Meaning is not checked. Bland, inaccurate or irrelevant copy can pass. Literal word lists miss synonyms and inflections unless added. Grammar rules overfit visible examples.
3. Context is not checked. A natural phrase can be flagged because the rule cannot tell whether it is appropriate. The if/verdict rule still flags "If the light is red, it's charging."
4. Facts are not verified. Claims such as "Acme cut checkout time in half after the migration" still escape detection. Evidence records are caller attestations.
5. Visuals are not reviewed. The flags can document a check but cannot perform it. Requiring images is an editorial choice, not a universal social rule.
6. The score is arbitrary. Multiple overlapping issues can deduct points for the same passage. It should not rank drafts or be presented as percent quality.

## Readiness

- Show v0.2.0 unchanged as a solid checker: **no**.
- Show the patch as a small experimental linter and invite critique: **yes, after the patch is published and its live state checked**.
- Give a content team an automatic publish gate: **no**.

The next useful investment is permission-cleared, independently rated good and bad copy, held apart from rule development. Report false alarms and misses by vocabulary, cadence and workflow checks. Do not claim overall performance from a handful of synthetic examples.
