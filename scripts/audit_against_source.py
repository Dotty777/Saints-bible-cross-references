"""Check every saved pair against a local Saints-Translation checkout.

The regular validators prove internal consistency (hashes, counts, anchors in the
readable files). This audit compares each completed pair with the pinned source
itself: the source unit text, every target reference, target anchor ID, target
text, continuation paragraphs and the pinned blob identity.

Usage:
    git clone https://github.com/Dotty777/Saints-Translation.git /tmp/saints-translation
    git -C /tmp/saints-translation checkout <commit pinned in the records>
    python scripts/audit_against_source.py /tmp/saints-translation
"""
from collections import Counter, defaultdict
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
# Three source books are stored as flat lists of {"chapter","ref","id","text"}.
FLAT_BOOKS = {'deuteronomy': 'Deuteronomy', 'leviticus': 'Leviticus', 'numbers': 'Numbers'}


def blob_sha(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def load_source(checkout):
    units, blobs = {}, {}
    for file in sorted(checkout.glob('*/verses.json')):
        rel = file.relative_to(checkout).as_posix()
        raw = file.read_bytes()
        blobs[rel] = blob_sha(raw)
        data = json.loads(raw)
        if isinstance(data, list):
            name = FLAT_BOOKS[rel.split('/')[0]]
            for unit in data:
                units[(rel, name + ' ' + unit['ref'])] = unit
            continue
        for chapter in data['chapters']:
            for unit in chapter['verses']:
                units[(rel, unit.get('reference', unit.get('ref')))] = unit
    return units, blobs


def record_files():
    yield from sorted(ROOT.glob('*/verses.json'))


def audit(checkout):
    units, blobs = load_source(checkout)
    issues, examples = Counter(), defaultdict(list)
    pairs = 0

    def flag(kind, detail):
        issues[kind] += 1
        if len(examples[kind]) < 20:
            examples[kind].append(detail)

    for file in record_files():
        data = json.loads(file.read_text(encoding='utf-8'))
        source_path = file.parent.name + '/verses.json'
        for chapter in data['chapters']:
            for verse in chapter['verses']:
                for edge in verse.get('cross_references', []):
                    pairs += 1
                    original = units.get((source_path, verse['reference']))
                    if original is None:
                        flag('source_reference_missing', [edge['id'], verse['reference']])
                    elif original['text'] != verse['text']:
                        flag('source_text_differs', [edge['id'], verse['reference']])
                    target = edge['target_source']
                    if blobs.get(target['path']) != target['blob_sha']:
                        flag('target_blob_differs', [edge['id'], target['path']])
                    for item in edge['target_verses']:
                        unit = units.get((target['path'], item['reference']))
                        if unit is None:
                            flag('target_reference_missing', [edge['id'], item['reference']])
                            continue
                        if unit['text'] != item['text']:
                            flag('target_text_differs', [edge['id'], item['reference']])
                        if item.get('id') and unit['id'] != item['id']:
                            flag('target_anchor_differs', [edge['id'], item['reference']])
                        if unit.get('continuation_paragraphs', []) != item.get('continuation_paragraphs', unit.get('continuation_paragraphs', [])):
                            flag('target_continuation_differs', [edge['id'], item['reference']])
    report = {'result': 'passed' if not issues else 'failed', 'checked_pairs': pairs,
              'issues': dict(issues), 'examples': dict(examples)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('checkout', type=Path, help='Path to a Saints-Translation checkout at the pinned commit')
    result = audit(parser.parse_args().checkout)
    raise SystemExit(0 if result['result'] == 'passed' else 1)
