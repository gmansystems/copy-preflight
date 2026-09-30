# Copy preflight

A local Python linter for repeated marketing phrases, a few rhetorical templates and copy-review reminders. It uses word lists and regexes. No API keys, model calls or third-party Python packages.

**This is an experimental linter, not an AI detector or a writing-quality gate.** It catches some familiar patterns. It misses bland writing that uses different words, and it can flag good writing. A score of 100 means no configured rule matched, not that the copy is good.

## Try it

Python 3.9+. Clone this repository and run from its directory:

```bash
printf '%s\n' 'Our platform empowers teams and unlocks their potential.' | python3 slopcheck.py
printf '%s\n' 'The operator restarted the pump.' | python3 slopcheck.py
python3 -m unittest -v
```

The first example produces vocabulary-review issues. The second has no issues under the public defaults. Neither result identifies the author or decides whether to publish.

Use `--input draft.txt` instead of stdin. Output is JSON:

- `issues`: rule codes, severity, edit advice and character spans where available.
- `status`: `blocked` if a block rule matched; otherwise `human_review`, even with no issues.
- `score`: 100 minus 20 per block and 7 per review, floored at zero. This weighting is arbitrary, not calibrated against reader ratings.
- `claims_detected`: only the text matched by the narrow claim patterns.

By default the process exits 0 after a valid run, including a blocked result. For scripts, use `--fail-on block` or `--fail-on review`. Exit 1 means the selected threshold matched; exit 2 means bad input or configuration. JSON is still printed on exit 1.

## What the rules do

| Check | Default behavior | Important limit |
| --- | --- | --- |
| Listed marketing phrases | Review | Literal phrases and selected inflections only; context can make a phrase appropriate |
| Teaser + question; question + if/verdict | Block | Narrow templates; legitimate questions can match |
| False contrasts, if/verdict, em-dash pivots, repeated short lines | Review | Style warnings, not proof of bad writing |
| Long sentences and social posts | Review | Word-count targets, not platform limits |
| Long social paragraphs | Block | A single newline wraps a paragraph; blank lines separate paragraphs |
| Numbers and selected claim verbs | Review | Misses many facts; can flag dates, versions or harmless numbers |
| Missing visual attestation on social channels | Block | Optional workflow policy; the tool cannot see images |

`--channel copy` is the default. `x`, `linkedin` and `instagram` enable social length checks and the visual policy. These are editorial presets, not claims about what each platform permits.

## Visual and source records

The social presets require a JSON file passed with `--visual visual.json`:

```json
{"inspected":true,"real_asset":true,"privacy_checked":true}
```

These must be JSON booleans, not strings. They record a caller's check. The tool cannot inspect pixels, confirm ownership or detect private information. Text-only posts can be reasonable: disable `social.visual_required` in a custom spec when this policy does not fit.

A source attestation passed with `--evidence evidence.json` can remove a matched claim reminder:

```json
[{"claim":"30%","source":"https://example.org/receipt","note":"The original receipt states this figure","checked":true}]
```

This is an illustrative record, not a real source. Each `claim` must match a detected phrase. The program does not fetch URLs or verify notes. Supplying a record does not make a claim true. Many claims produce no reminder at all.

## Configure it

Copy `spec.json`, edit it, and pass `--spec my-spec.json`. Public vocabulary is review-only; use `lexicon.hard` for words your own workflow must block. The default `linkedin_blocked_terms` list is empty. Grammar patterns are in `slopcheck.py`; the `grammar` section in the spec describes them, it does not change the regexes.

Input is processed locally by this code. It makes no network calls. Do not put private messages or customer data in public issues, examples or test fixtures.

## Test status and known misses

The audit patch has 32 automated tests. They check specific behavior, not detection accuracy. See [AUDIT.md](AUDIT.md) for the v0.2.0 defects, fixes and remaining limits.

The following factual claims still produce no claim reminders:

- "Acme cut checkout time in half after the migration."
- "The update ships tomorrow and supports every Android phone."

No held-out, human-rated benchmark has been run. Precision and recall are unknown. More regexes will not establish that this tool catches slop well. Before using it as a team gate, test it on permission-cleared drafts rated by readers, separate those examples from rule development, and measure both missed bad copy and needless alarms on good copy.

Run `python3 -m unittest -v`. Contributions should include a failing test and explain the false-positive tradeoff. MIT license.
