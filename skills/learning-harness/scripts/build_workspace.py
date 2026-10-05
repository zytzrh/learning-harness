#!/usr/bin/env python3
"""Build a self-contained agent-taught learning workspace. No model API calls."""
import argparse
import json
from pathlib import Path
from uuid import uuid4


def build(payload):
    if payload.get('schema_version') == 2:
        state = payload
    else:
        goal = payload.get('goal')
        paragraphs = payload.get('paragraphs')
        if not isinstance(goal, str) or not 0 < len(goal.strip()) <= 500:
            raise ValueError('goal must contain 1–500 characters')
        if not isinstance(paragraphs, list) or not 1 <= len(paragraphs) <= 100:
            raise ValueError('Provide 1–100 paragraphs')
        if any(not isinstance(p, str) or not p.strip() or len(p) > 12000 for p in paragraphs):
            raise ValueError('Each paragraph must contain 1–12000 characters')
        cid = uuid4().hex
        state = dict(schema_version=2, id=uuid4().hex, revision=0, goal=goal.strip(),
                     blocks=[dict(id=uuid4().hex, text=p, concept_id=cid) for p in paragraphs],
                     concepts=[dict(id=cid, name=goal.strip(), status='unseen', evidence=[])],
                     stack=[cid], annotations=[], events=[], operations=[])
    assets = Path(__file__).resolve().parent.parent / 'assets'
    page = (assets / 'workspace.html').read_text()
    # Replace fixed template slots in one pass; user data cannot introduce slots.
    import re
    replacements = {'__STATE__': json.dumps(state, ensure_ascii=False).replace('<', '\\u003c'),
                    '__STYLE__': (assets / 'style.css').read_text(),
                    '__ENGINE__': (assets / 'state.js').read_text(),
                    '__CLIENT__': (assets / 'client.js').read_text()}
    page = re.sub(r'__(?:STATE|STYLE|ENGINE|CLIENT)__', lambda m: replacements[m.group()], page)
    return page, state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='JSON: {goal, paragraphs} or an exported v2 snapshot')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--state-output', type=Path, help='Optional initial checkpoint; do not overwrite a newer live snapshot')
    args = parser.parse_args()
    payload = json.loads(args.input.read_text())
    if not isinstance(payload, dict):
        parser.error('Expected a JSON object')
    page, state = build(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(page)
    if args.state_output:
        args.state_output.parent.mkdir(parents=True, exist_ok=True)
        args.state_output.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    print(args.output)

if __name__ == '__main__':
    main()
