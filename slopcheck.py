#!/usr/bin/env python3
"""Conservative, deterministic preflight. stdlib only. Never a truth verifier."""
import argparse
import json
import re
import sys
from pathlib import Path

SPEC = json.loads((Path(__file__).parent / 'spec.json').read_text())
WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def issue(code, severity, message, fix, start=None, end=None):
    return dict(code=code, severity=severity, message=message, fix=fix, span=[start, end] if start is not None else None)


def lint(text, channel='copy', visual=None, evidence=None):
    if channel not in ('copy', 'x', 'linkedin', 'instagram'):
        raise ValueError('channel must be copy, x, linkedin, or instagram')
    evidence = evidence or []
    out = []
    if not text.strip():
        out.append(issue('EMPTY', 'block', 'No copy supplied.', 'Write a concrete line.'))
    # Match phrases at word boundaries, ignoring case; list order never duplicates a span.
    occupied = set()
    for severity, words in SPEC['lexicon'].items():
        for phrase in words:
            pattern = re.compile(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', re.I)
            for m in pattern.finditer(text):
                if any(x in occupied for x in range(m.start(), m.end())):
                    continue
                occupied.update(range(m.start(), m.end()))
                out.append(issue('BANNED_REGISTER' if severity == 'hard' else 'GENERIC_REGISTER',
                                 'block' if severity == 'hard' else 'review',
                                 f'Generic phrase: {m.group(0)!r}.',
                                 'Replace with a named thing, observed result, or plain verb.', m.start(), m.end()))
    if channel != 'copy':
        max_words = SPEC['social'][f'max_words_{channel}']
        n = len(WORD.findall(text))
        if n > max_words:
            out.append(issue('POST_LENGTH', 'review', f'{n} words; target <= {max_words}.', 'Cut to one point and its proof.'))
        pos = 0
        for paragraph in text.split('\n'):
            n = len(WORD.findall(paragraph))
            if n > SPEC['social']['max_paragraph_words']:
                out.append(issue('WALL_OF_TEXT', 'block', f'{n}-word unbroken line.',
                                 'Break into short lines and cut the second idea.', pos, pos + len(paragraph)))
            pos += len(paragraph) + 1
        if not visual or not visual.get('inspected') or not visual.get('real_asset') or not visual.get('privacy_checked'):
            out.append(issue('VISUAL_UNVERIFIED', 'block', 'No inspected, real, privacy-checked visual.',
                             'Attach a real screenshot/photo and inspect pixels, crop, provenance and private details.'))
        if channel == 'linkedin' and SPEC.get('linkedin_blocked_terms'):
            for term in SPEC['linkedin_blocked_terms']:
                if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I):
                    out.append(issue('LINKEDIN_LANE', 'block', 'Configured term disallowed on LinkedIn.',
                                     'Choose a topic that fits this audience, or skip this channel.'))
    # A small, explicit grammar layer. These are format warnings, never AI-authorship labels.
    def add_grammar(code, severity, message, fix, start, end):
        out.append(issue(code, severity, message, fix, start, end))

    # Concrete, narrow constructions, with spans so a human can edit the right part.
    templates = [
        ('RHETORICAL_SETUP', 'block',
         r"\b(?:has|comes down to|boils down to|there is|there's|here's)\s+(?:one|a single)\s+(?:test|question|thing|rule)\s*:\s*(?:\n\s*)?[^?\n]{3,100}\?",
         'Say what happened or what you checked, without the teaser and staged question.'),
        ('QUESTION_IF_VERDICT', 'block',
         r"(?:^|(?<=\n))\s*[^?\n]{3,100}\?\s*(?:\n\s*)+If\s+[^\n.!?]{3,100},\s*(?:it(?:'s| is)|that(?:'s| is))\s+[^\n.!?]{2,100}[.!]?",
         'Replace the rhetorical question and verdict with the observed result and source.'),
        ('FALSE_CONTRAST', 'review',
         r"\bnot\s+(?:just\s+)?[^,.!?\n]{2,90}?,?\s+but\s+(?:also\s+)?[^.!?\n]{2,90}",
         'Say the specific point once instead of opposing two vague labels.'),
        ('EM_DASH_PIVOT', 'review',
         r"[^\n.!?]{3,90}\s*—\s*[^\n.!?]{3,90}",
         'Try a plain sentence with the specific action or result.'),
        ('AI_OPENER', 'review',
         r"(?:^|(?<=\n))\s*(?:here(?:'|’)s the thing|let that sink in|the real question is|at the end of the day)\b[^\n]*",
         'Remove the throat-clearing and lead with the real observation.'),
    ]
    for code, severity, pattern, fix in templates:
        for m in re.finditer(pattern, text, re.I | re.M):
            add_grammar(code, severity, f'Template cadence: {m.group().strip()!r}.', fix, m.start(), m.end())
    for m in re.finditer(r"(?:^|(?<=\n))\s*If\s+[^\n.!?]{3,100},\s*(?:it(?:'s| is)|that(?:'s| is))\s+[^\n.!?]{2,100}[.!]?", text, re.I):
        if not any(i['code'] == 'QUESTION_IF_VERDICT' and i['span'] and i['span'][0] <= m.start() < i['span'][1] for i in out):
            add_grammar('IF_THEN_APHORISM', 'review', 'If/then verdict cadence.',
                        'Name the observed result, not a general moral.', m.start(), m.end())
    if channel != 'copy':
        # A three-line fragment stack is a weak signal, so review only.
        lines = [(i, x.strip()) for i, x in enumerate(text.splitlines()) if x.strip()]
        for j in range(len(lines)-2):
            batch = [x for _, x in lines[j:j+3]]
            if all(1 <= len(WORD.findall(x)) <= 7 for x in batch) and all(x.endswith(('.', '!', '?')) for x in batch):
                first = lines[j][0]
                pos = sum(len(x) + 1 for x in text.splitlines()[:first])
                add_grammar('FRAGMENT_STACK', 'review', 'Three short punchline lines in a row.',
                            'Use natural sentence rhythm; keep only the line with a concrete observation.', pos, pos + sum(len(x) for x in batch)+2)
                break
        for j in range(len(lines)-2):
            batch = [x for _, x in lines[j:j+3]]
            # Detect repeated *openers*, not any list with three items.
            starts = [' '.join(WORD.findall(x)[:2]).lower() for x in batch]
            if starts[0] and starts.count(starts[0]) == 3 and len(WORD.findall(batch[0])) >= 3:
                first = lines[j][0]
                pos = sum(len(x) + 1 for x in text.splitlines()[:first])
                add_grammar('RULE_OF_THREE', 'review', 'Three lines reuse the same opening.',
                            'Keep the strongest example; vary rhythm only if it helps the point.', pos, pos + sum(len(x) for x in batch)+2)
                break
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        n = len(WORD.findall(sentence))
        if n > SPEC['social']['max_sentence_words']:
            out.append(issue('LONG_SENTENCE', 'review', f'{n}-word sentence.', 'Cut the setup and keep one concrete point.'))
    claims = []
    seen = set()
    for pat in SPEC['claim_patterns']:
        for m in re.finditer(pat, text, re.I):
            if (m.start(), m.end()) in seen:
                continue
            seen.add((m.start(), m.end()))
            claims.append({'text': m.group(), 'span': [m.start(), m.end()]})
    if claims:
        # Evidence is claim-specific and must explicitly be marked checked. Merely supplying URLs cannot pass.
        supported = {e.get('claim', '').casefold() for e in evidence if e.get('checked') is True and e.get('source') and e.get('note')}
        missing = [c for c in claims if c['text'].casefold() not in supported]
        if missing:
            out.append(issue('CLAIM_REVIEW', 'block', 'Checkable phrases need claim-specific source checks: ' + ', '.join(repr(c['text']) for c in missing),
                             'Verify each claim at the original source, add a source and what it proves, or remove the claim.'))
    out.sort(key=lambda x: (x['span'][0] if x['span'] else len(text) + 1, x['code']))
    # Score describes surface problems only. A zero-issue result is not permission to publish.
    deductions = {'block': 20, 'review': 7}
    score = max(0, 100 - sum(deductions[i['severity']] for i in out))
    return {'score': score, 'status': 'blocked' if any(i['severity'] == 'block' for i in out) else 'human_review',
            'issues': out, 'claims_detected': claims, 'note': 'Heuristic preflight only. A human must verify facts, voice, image pixels, audience and current context.'}


def main():
    p = argparse.ArgumentParser(description='Conservative anti-slop preflight; output JSON')
    p.add_argument('--channel', choices=['copy', 'x', 'linkedin', 'instagram'], default='copy')
    p.add_argument('--input', help='UTF-8 text file; defaults to stdin')
    p.add_argument('--visual', help='JSON file with inspected, real_asset, privacy_checked booleans')
    p.add_argument('--evidence', help='JSON array of claim, source, note, checked records')
    args = p.parse_args()
    text = Path(args.input).read_text() if args.input else sys.stdin.read()
    visual = json.loads(Path(args.visual).read_text()) if args.visual else None
    evidence = json.loads(Path(args.evidence).read_text()) if args.evidence else None
    print(json.dumps(lint(text, args.channel, visual, evidence), indent=2))


if __name__ == '__main__':
    main()
