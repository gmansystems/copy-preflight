#!/usr/bin/env python3
"""Conservative, deterministic preflight. stdlib only. Never a truth verifier."""
import argparse
import json
import re
import sys
from pathlib import Path

SPEC = json.loads((Path(__file__).parent / 'spec.json').read_text(encoding='utf-8'))
WORD = re.compile(r"\b[\w'-]+\b", re.UNICODE)


def issue(code, severity, message, fix, start=None, end=None):
    return dict(code=code, severity=severity, message=message, fix=fix, span=[start, end] if start is not None else None)


def validate_spec(config):
    """Reject malformed settings rather than silently changing policy."""
    if not isinstance(config, dict):
        raise ValueError('spec must be an object')
    lexicon = config.get('lexicon')
    if not isinstance(lexicon, dict) or set(lexicon) != {'hard', 'soft'}:
        raise ValueError('lexicon must contain hard and soft lists')
    for values in lexicon.values():
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError('lexicon entries must be nonempty strings')
    social = config.get('social')
    if not isinstance(social, dict):
        raise ValueError('social must be an object')
    for key in ('max_words_x', 'max_words_linkedin', 'max_words_instagram', 'max_paragraph_words', 'max_sentence_words'):
        if type(social.get(key)) is not int or social[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    if type(social.get('visual_required', True)) is not bool:
        raise ValueError('visual_required must be a boolean')
    for key in ('claim_patterns', 'linkedin_blocked_terms'):
        values = config.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            raise ValueError(f'{key} must be a list of nonempty strings')
    for pattern in config.get('claim_patterns', []):
        re.compile(pattern)


def lint(text, channel='copy', visual=None, evidence=None, spec=None):
    config = SPEC if spec is None else spec
    validate_spec(config)
    if not isinstance(text, str):
        raise ValueError('text must be a string')
    if visual is not None and (not isinstance(visual, dict) or any(type(visual.get(k)) is not bool for k in ('inspected', 'real_asset', 'privacy_checked'))):
        raise ValueError('visual must be an object with inspected, real_asset, privacy_checked booleans')
    if evidence is not None:
        if not isinstance(evidence, list) or any(not isinstance(e, dict) or not isinstance(e.get('claim'), str) or not isinstance(e.get('source'), str) or not isinstance(e.get('note'), str) or type(e.get('checked')) is not bool for e in evidence):
            raise ValueError('evidence must be an array of claim, source, note strings and checked booleans')
    if channel not in ('copy', 'x', 'linkedin', 'instagram'):
        raise ValueError('channel must be copy, x, linkedin, or instagram')
    evidence = evidence or []
    out = []
    if not text.strip():
        out.append(issue('EMPTY', 'block', 'No copy supplied.', 'Write a concrete line.'))
    # Match phrases at word boundaries, ignoring case; list order never duplicates a span.
    occupied = set()
    for severity, words in config['lexicon'].items():
        for phrase in words:
            pattern = re.compile(r'(?<!\w)' + re.escape(phrase.replace('’', "'")).replace("'", "['’]") + r'(?!\w)', re.I)
            for m in pattern.finditer(text):
                if any(x in occupied for x in range(m.start(), m.end())):
                    continue
                occupied.update(range(m.start(), m.end()))
                out.append(issue('BANNED_REGISTER' if severity == 'hard' else 'GENERIC_REGISTER',
                                 'block' if severity == 'hard' else 'review',
                                 f'Generic phrase: {m.group(0)!r}.',
                                 'Replace with a named thing, observed result, or plain verb.', m.start(), m.end()))
    if channel != 'copy':
        max_words = config['social'][f'max_words_{channel}']
        n = len(WORD.findall(text))
        if n > max_words:
            out.append(issue('POST_LENGTH', 'review', f'{n} words; target <= {max_words}.', 'Cut to one point and its proof.'))
        # A single newline wraps a paragraph; only a blank line separates paragraphs.
        for m in re.finditer(r'[^\n]+(?:\n(?![ \t]*\n)[^\n]+)*', text):
            n = len(WORD.findall(m.group()))
            if n > config['social']['max_paragraph_words']:
                out.append(issue('WALL_OF_TEXT', 'block', f'{n}-word paragraph.',
                                 'Split paragraphs and cut the second idea.', m.start(), m.end()))
        if config['social'].get('visual_required', True) and (not visual or not all(visual.get(k) is True for k in ('inspected', 'real_asset', 'privacy_checked'))):
            out.append(issue('VISUAL_UNVERIFIED', 'block', 'No inspected, real, privacy-checked visual.',
                             'Inspect the actual asset for crop, provenance and private details.'))
        if channel == 'linkedin' and config.get('linkedin_blocked_terms'):
            for term in config['linkedin_blocked_terms']:
                if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I):
                    out.append(issue('LINKEDIN_LANE', 'block', 'Configured term disallowed on LinkedIn.',
                                     'Choose a topic that fits this audience, or skip this channel.'))
    # A small, explicit grammar layer. These are format warnings, never AI-authorship labels.
    def add_grammar(code, severity, message, fix, start, end):
        out.append(issue(code, severity, message, fix, start, end))

    # Concrete, narrow constructions, with spans so a human can edit the right part.
    templates = [
        ('RHETORICAL_SETUP', 'block',
         r"\b(?:has|comes down to|boils down to|there is|there['’]s|here['’]s)\s+(?:one|a single)\s+(?:test|question|thing|rule)\s*:\s*(?:\n\s*)?[^?\n]{3,100}\?",
         'Say what happened or what you checked, without the teaser and staged question.'),
        ('QUESTION_IF_VERDICT', 'block',
         r"(?:^|(?<=\n))\s*[^?\n]{3,100}\?\s*(?:\n\s*)+If\s+[^\n.!?]{3,100},\s*(?:it(?:['’]s| is)|that(?:['’]s| is))\s+[^\n.!?]{2,100}[.!]?",
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
    for m in re.finditer(r"(?:^|(?<=\n))\s*If\s+[^\n.!?]{3,100},\s*(?:it(?:['’]s| is)|that(?:['’]s| is))\s+[^\n.!?]{2,100}[.!]?", text, re.I):
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
                            'Use natural sentence rhythm; keep only the line with a concrete observation.', pos, sum(len(x) + 1 for x in text.splitlines()[:lines[j+2][0]]) + len(text.splitlines()[lines[j+2][0]]))
                break
        for j in range(len(lines)-2):
            batch = [x for _, x in lines[j:j+3]]
            # Detect repeated *openers*, not any list with three items.
            starts = [' '.join(WORD.findall(x)[:2]).lower() for x in batch]
            if starts[0] and starts.count(starts[0]) == 3 and len(WORD.findall(batch[0])) >= 3:
                first = lines[j][0]
                pos = sum(len(x) + 1 for x in text.splitlines()[:first])
                add_grammar('RULE_OF_THREE', 'review', 'Three lines reuse the same opening.',
                            'Keep the strongest example; vary rhythm only if it helps the point.', pos, sum(len(x) + 1 for x in text.splitlines()[:lines[j+2][0]]) + len(text.splitlines()[lines[j+2][0]]))
                break
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', text):
        n = len(WORD.findall(sentence))
        if n > config['social']['max_sentence_words']:
            out.append(issue('LONG_SENTENCE', 'review', f'{n}-word sentence.', 'Cut the setup and keep one concrete point.'))
    claims = []
    seen = set()
    for pat in config['claim_patterns']:
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
            out.append(issue('CLAIM_REVIEW', 'review', 'Checkable phrases need claim-specific source checks: ' + ', '.join(repr(c['text']) for c in missing),
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
    p.add_argument('--spec', help='Alternative spec JSON file; defaults to bundled spec.json')
    p.add_argument('--fail-on', choices=['block', 'review'], help='Exit 1 for blocks, or for any issue; default exits 0')
    args = p.parse_args()
    try:
        text = Path(args.input).read_text(encoding='utf-8') if args.input else sys.stdin.read()
        visual = json.loads(Path(args.visual).read_text(encoding='utf-8')) if args.visual else None
        evidence = json.loads(Path(args.evidence).read_text(encoding='utf-8')) if args.evidence else None
        config = json.loads(Path(args.spec).read_text(encoding='utf-8')) if args.spec else SPEC
        result = lint(text, args.channel, visual, evidence, config)
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError, re.error) as exc:
        print(f'Input/config error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return int(bool(args.fail_on) and (result['status'] == 'blocked' or (args.fail_on == 'review' and bool(result['issues']))))


if __name__ == '__main__':
    sys.exit(main())
