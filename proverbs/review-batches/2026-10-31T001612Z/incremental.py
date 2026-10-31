"""Current Proverbs batch only. All preparation is scratch; --apply is explicit.

Commands: --baseline, --required-sources, --refresh-sources, --preflight,
--apply, --audit-local, --readback GIT_REF, --publication-check GIT_REF.
Historical records stay immutable Git objects; no older helper is imported.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime, timezone
import argparse, contextlib, csv, hashlib, importlib.util, io, json, os, re
import subprocess, sys, urllib.request, uuid

sys.dont_write_bytecode = True  # Read production helpers without touching their directories.

HERE = Path(__file__).resolve().parent
REPO = HERE.parent / 'saints-crossrefs'
CACHE = HERE.parent / 'reference'
CONFIG = json.loads((HERE / 'run-config.json').read_text(encoding='utf-8-sig'))
RUN, DATE, BASE, PIN = (CONFIG[k] for k in ['run_id', 'date', 'baseline_commit', 'source_commit'])
STEMS = {'proverbs-5-10': list(range(5, 11)), 'proverbs-11-16': list(range(11, 17)), 'proverbs-17-23': list(range(17, 24))}
SOURCE_REPO = 'Dotty777/Saints-Translation'
ARCHIVE = 'proverbs/review-batches/' + RUN + '/'
ALLOWED_NT = {'scripts/render_new_testament.py', 'scripts/validate_new_testament.py'}
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / 'scripts'))
from passages import INDEX, keys, complete_text
from chapter_structure import chapter_units, completed_chapter_numbers, completed_source_sections

def require(ok, message):
    if not ok: raise ValueError(message)
def load(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def encoded(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def digest(path): return sha(Path(path).read_bytes())
def text_sha(value): return sha(value.encode('utf-8'))
def blob(raw): return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
def flat(data): return [v for c in data['chapters'] for v in c['verses']]
def slug(value): return re.sub('[^a-z0-9]+', '-', value.lower()).strip('-')
def git(*args): return subprocess.check_output(['git', *args], cwd=REPO)
def original(path, ref=BASE): return git('show', ref + ':' + path)
def is_nt(path): return path.startswith('new-testament/') or path in ALLOWED_NT
def without_nt(progress): return {k: v for k, v in progress.items() if k != 'new_testament_tracker'}
def safe_path(root, relative):
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()) and path.resolve() != root.resolve(), 'Unsafe path: ' + relative)
    node = path
    while node != root:
        require(not node.is_symlink(), 'Symlink path: ' + relative); node = node.parent
    return path
def module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result

def baseline():
    paths = ['canon.json', 'progress.json'] + ['proverbs/' + n + '.json' for n in ['verses', 'source-checks', 'inventory', 'editorial-notes', 'verification']]
    identities = {}
    for path in paths:
        raw = original(path); saved = HERE / ('before-' + path.replace('/', '__'))
        require(json.loads(raw) == load(saved), 'Before snapshot differs: ' + path)
        identities[path] = {'git_blob_sha': blob(raw), 'snapshot_sha256': digest(saved)}
    p = load(HERE / 'before-progress.json'); b = load(HERE / 'before-proverbs__verses.json')
    require(len(p['runs']) == 38 and not any(r.get('run_id') == RUN for r in p['runs']), 'Historical runs changed')
    require((p['completed_source_verses'], p['completed_cross_references'], p['completed_chapters']) == (16680, 21437, 440), 'Baseline totals changed')
    require((len(flat(b)), len(chapter_units(b)), len(b['chapters'])) == (939, 31, 34), 'Native inventory changed')
    require((b['completed_source_verses'], b['completed_cross_references']) == (119, 133), 'Proverbs baseline changed')
    cohort = [v['reference'] for c in b['chapters'] if c['chapter'] in CONFIG['planned_native_chapters'] for v in c['verses']]
    require(len(cohort) == 572 and len(set(cohort)) == 572, 'Unexpected source cohort')
    return {'run_id': RUN, 'baseline_commit': BASE, 'source_commit': PIN, 'historical_runs': 38,
            'source_units_in_cohort': len(cohort), 'native_chapters': 31, 'source_sections': 34,
            'files': identities, 'completion_credit': 0}

def current_base():
    """Allow an independent NT commit or dirty NT files without rebasing OT work."""
    baseline()
    head = git('rev-parse', 'HEAD').decode().strip()
    changed = git('diff', '--name-only', BASE, head).decode().splitlines()
    for path in changed:
        require(is_nt(path) or path == 'progress.json', 'Concurrent OT commit: ' + path)
    p = load(REPO / 'progress.json'); before = load(HERE / 'before-progress.json')
    require(without_nt(p) == without_nt(before), 'Current OT progress differs from review baseline')
    dirty = git('diff', '--name-only', 'HEAD').decode().splitlines()
    for path in dirty:
        require(is_nt(path) or path == 'progress.json', 'Concurrent OT working edit: ' + path)
    for path in ['canon.json', 'proverbs/verses.json', 'proverbs/source-checks.json', 'proverbs/inventory.json', 'proverbs/editorial-notes.json', 'proverbs/verification.json', 'scripts/chapter_structure.py', 'scripts/render_books.py', 'scripts/validate.py']:
        require((REPO / path).read_bytes().replace(b'\r\n', b'\n') == original(path).replace(b'\r\n', b'\n'), 'Protected file changed: ' + path)
    return p, head

def receipt_path(stem, peer=False):
    suffix = '-peer-review.json' if peer else '-reading-receipt.json'
    path = HERE / (stem + suffix)
    if not peer and not path.exists(): path = HERE / (stem + '-review.json')
    # Accept the conventional peer-reading-receipt name, without rewriting evidence.
    if peer and not path.exists(): path = HERE / (stem + '-peer-reading-receipt.json')
    require(path.exists(), 'Missing receipt: ' + path.name)
    return path

def receipt(stem, peer=False):
    path = receipt_path(stem, peer); captured = path.read_bytes(); r = json.loads(captured)
    for k, value in [('run_id', RUN), ('base_commit', BASE), ('source_commit', PIN), ('source_book', 'Proverbs'), ('reviewed', DATE), ('review_timezone', 'America/New_York')]:
        require(r.get(k) == value, 'Receipt identity ' + path.name + ': ' + k)
    require(r.get('source_chapters') == STEMS[stem], 'Receipt native chapter scope: ' + stem)
    require(isinstance(r.get('reviewer'), str) and r['reviewer'].strip(), 'Missing reviewer: ' + stem)
    for kind in ['tsv', 'cases']:
        filename = stem + ('.tsv' if kind == 'tsv' else '-cases.json')
        require(r.get(kind + '_file') == filename and r.get(kind + '_sha256') == digest(HERE / filename), 'Stale receipt ' + kind + ' hash: ' + path.name)
    require(isinstance(r.get('context_references'), list), 'Missing explicit context list: ' + path.name)
    for ref in r['context_references']: keys(ref)
    for field in ['reread_evidence', 'reading_log']:
        evidence_record = r.get(field)
        if isinstance(evidence_record, dict) and 'file' in evidence_record:
            file = safe_path(HERE, evidence_record['file'])
            require(file.parent == HERE and evidence_record.get('sha256') == digest(file), 'Changed optional reading evidence: ' + path.name)
    if peer:
        author_path, author = receipt(stem)
        require(r.get('author_sha256') == digest(author_path) and r.get('disposition') == 'accepted', 'Peer does not accept final author packet: ' + stem)
        require(r['reviewer'] != author['reviewer'], 'Peer reviewer must be distinct from author: ' + stem)
        require(r.get('complete_source_target_rationale_triples_read') is True, 'Peer triple reading missing: ' + stem)
    else:
        for flag in ['all_source_verses_read', 'all_target_passages_read', 'necessary_context_read', 'all_retained_rationales_reread']:
            require(r.get(flag) is True, 'Missing author reading attestation: ' + flag)
    require(path.read_bytes() == captured, 'Receipt changed during validation: ' + path.name)
    return path, r

def packets(require_peers=True):
    before = load(HERE / 'before-proverbs__verses.json'); result = {}; all_pairs = set()
    for stem, chapters in STEMS.items():
        packet_paths = [HERE / (stem + '.tsv'), HERE / (stem + '-cases.json'), receipt_path(stem)]
        if require_peers: packet_paths.append(receipt_path(stem, True))
        captured = {p.name: p.read_bytes() for p in packet_paths}
        with io.StringIO(captured[stem + '.tsv'].decode('utf-8-sig'), newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            require(reader.fieldnames == ['source_reference', 'target', 'relationship', 'rationale'], 'TSV schema: ' + stem)
            rows = list(reader)
        cases = json.loads(captured[stem + '-cases.json'])
        require(set(cases) == {'deferred_source_units', 'unresolved_candidates', 'unread_hints'}, 'Cases schema: ' + stem)
        cohort = [v['reference'] for c in before['chapters'] if c['chapter'] in chapters for v in c['verses']]
        deferred = cases['deferred_source_units']; candidates = cases['unresolved_candidates']
        refs = {row['source_reference'] for row in rows}; drefs = [d['source_reference'] for d in deferred]
        require(len(drefs) == len(set(drefs)) and not refs.intersection(drefs), 'Duplicate or supported deferral: ' + stem)
        require(refs | set(drefs) == set(cohort), 'Every read source must be retained or deferred: ' + stem)
        for row in rows:
            require(all(isinstance(value, str) and value.strip() for value in row.values()), 'Empty retained field')
            target_keys = keys(row['target']); pair = (row['source_reference'], tuple(target_keys))
            require(row['source_reference'] not in target_keys and pair not in all_pairs, 'Self or duplicate pair: ' + str(pair)); all_pairs.add(pair)
        for case in deferred + candidates:
            require(case['source_reference'] in cohort and isinstance(case.get('reason'), str) and case['reason'].strip(), 'Invalid case source/reason')
            require(case.get('completed_source_credit', 0) == 0 and case.get('completed_pair_credit') == 0, 'Pending case completion credit')
        for case in deferred:
            require(case.get('target') is None and case.get('source_unit_read', True) is True, 'Deferred source must be targetless and read within the attested source cohort')
        for case in candidates:
            keys(case['target'])
            require(case.get('retained', False) is False and case.get('source_and_target_read', case.get('source_and_target_text_read')) is True, 'Candidate must be unretained and actually read')
        for hint in cases['unread_hints']:
            require(hint.get('completed_source_credit', 0) == 0 and hint.get('completed_pair_credit', 0) == 0, 'Unread hint earns credit')
            require(hint.get('source_and_target_read', hint.get('source_and_target_text_read', False)) is False, 'Unread hint declared read')
        author_file, author = receipt(stem)
        require(author_file.name in captured and author == json.loads(captured[author_file.name]), 'Author receipt changed after packet capture')
        require(author['tsv_sha256'] == sha(captured[stem + '.tsv']) and author['cases_sha256'] == sha(captured[stem + '-cases.json']), 'Author receipt differs from parsed packet bytes')
        for k, count in [('source_units_read', len(cohort)), ('completed_source_verses', len(refs)), ('completed_pairs', len(rows))]:
            require(author.get(k) == count, 'Author count mismatch: ' + stem + ' ' + k)
        peer_file, peer = receipt(stem, True) if require_peers else (None, None)
        if peer:
            require(peer_file.name in captured and peer == json.loads(captured[peer_file.name]), 'Peer receipt changed after packet capture')
            require(peer['author_sha256'] == sha(captured[author_file.name]), 'Peer accepted a different captured author receipt')
        for r in [author] + ([peer] if peer else []):
            for field in ['reread_evidence', 'reading_log']:
                record = r.get(field)
                if isinstance(record, dict) and 'file' in record:
                    raw = (HERE / record['file']).read_bytes(); require(sha(raw) == record['sha256'], 'Optional reading evidence changed')
                    captured[record['file']] = raw
        frozen = {name: sha(raw) for name, raw in captured.items()}
        require(all(digest(HERE / name) == value for name, value in frozen.items()), 'Packet changed during validation: ' + stem)
        result[stem] = dict(rows=rows, cases=cases, cohort=cohort, supported=refs, author=author, author_file=author_file, peer=peer, peer_file=peer_file, frozen_inputs=frozen)
    require(sum(len(p['cohort']) for p in result.values()) == 572, 'Incorrect cohort size')
    return result

def required_sources(require_peers=False):
    plans = packets(require_peers); books = {'Proverbs'}
    for p in plans.values():
        refs = [r['target'] for r in p['rows']] + [c['target'] for c in p['cases']['unresolved_candidates']] + p['author']['context_references']
        if p['peer']: refs += p['peer']['context_references']
        for ref in refs: books.update(INDEX[k]['book'] for k in keys(ref))
    canon = {b['book'] for b in load(REPO / 'canon.json')['books']}
    require(books <= canon, 'Noncanonical source book')
    index = {b['book']: b for b in load(CACHE / 'progress.json')['books']}
    return [{'book': book, 'path': index[book]['records'] + 'verses.json', 'cache_file': Path(index[book]['records'].rstrip('/')).name + '.json'} for book in sorted(books)]

def refresh_sources():
    """Fetch full raw bytes; compact GitHub plugin identity files may be supplied first."""
    requested = required_sources(require_peers=False)
    # Include peer context whenever final peer receipts already exist.
    try: requested = required_sources(require_peers=True)
    except (ValueError, FileNotFoundError): pass
    entries = []; files = []; fetched = datetime.now(timezone.utc).isoformat()
    for spec in requested:
        stem = Path(spec['cache_file']).stem
        identity_file = stem + '-identity.json'; identity_path = HERE / identity_file
        if identity_path.exists():
            metadata = load(identity_path)
        else:
            url = f'https://api.github.com/repos/{SOURCE_REPO}/contents/{spec["path"]}?ref={PIN}'
            req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'Codex-Proverbs-Review'})
            with urllib.request.urlopen(req, timeout=45) as response: payload = json.load(response)
            metadata = {'repository': SOURCE_REPO, 'ref': PIN, 'path': spec['path'], 'sha': payload['sha'], 'fetched_at_utc': fetched, 'method': 'GitHub contents API at exact commit'}
            identity_path.write_bytes(encoded(metadata))
        require((metadata['repository'], metadata['ref'], metadata['path']) == (SOURCE_REPO, PIN, spec['path']), 'Wrong fresh identity: ' + spec['book'])
        url = f'https://raw.githubusercontent.com/{SOURCE_REPO}/{PIN}/{spec["path"]}'
        with urllib.request.urlopen(url, timeout=45) as response: raw = response.read()
        require(blob(raw) == metadata['sha'], 'Raw source Git blob differs: ' + spec['book'])
        value = json.loads(raw)
        require(value == load(CACHE / spec['cache_file']) and (isinstance(value, list) or value.get('book') == spec['book']), 'Complete cache/source differs: ' + spec['book'])
        raw_file = stem + '-pinned-original.json'; (HERE / raw_file).write_bytes(raw)
        entry = {**spec, 'commit': PIN, 'blob_sha': blob(raw), 'raw_file': raw_file, 'raw_sha256': sha(raw), 'identity_file': identity_file, 'identity_sha256': digest(identity_path), 'raw_url': url, 'full_parsed_cache_equal': True, 'completion_credit': 0}
        entries.append(entry); files.extend([raw_file, identity_file])
        print(json.dumps({'source_verified': spec['book'], 'blob_sha': entry['blob_sha']}), flush=True)
    registry = {'run_id': RUN, 'source_repository': SOURCE_REPO, 'source_commit': PIN, 'fetched_at_utc': fetched, 'books': entries, 'files': files, 'completion_credit': 0}
    (HERE / 'source-registry.json').write_bytes(encoded(registry)); return registry

def verified_registry():
    registry = load(HERE / 'source-registry.json')
    require((registry['run_id'], registry['source_commit'], registry['source_repository']) == (RUN, PIN, SOURCE_REPO), 'Registry identity')
    required_specs = {s['book']: s for s in required_sources(True)}
    required = set(required_specs); found = {s['book'] for s in registry['books']}
    require(required <= found and len(found) == len(registry['books']), 'Missing or duplicate retained/candidate/context source pins')
    for entry in registry['books']:
        if entry['book'] in required_specs:
            require(all(entry[k] == required_specs[entry['book']][k] for k in ['path', 'cache_file']), 'Source book/path mismatch')
        raw = (HERE / entry['raw_file']).read_bytes(); identity = load(HERE / entry['identity_file'])
        require(sha(raw) == entry['raw_sha256'] and blob(raw) == entry['blob_sha'] == identity['sha'], 'Pinned full source hashes changed')
        require(digest(HERE / entry['identity_file']) == entry['identity_sha256'], 'Identity evidence changed')
        require((identity['repository'], identity['ref'], identity['path']) == (SOURCE_REPO, PIN, entry['path']), 'Pin identity mismatch')
        parsed = json.loads(raw)
        require(parsed == load(CACHE / entry['cache_file']) and (isinstance(parsed, list) or parsed.get('book') == entry['book']), 'Full cache/book changed after source fetch')
    return registry

def evidence(reference):
    unit = deepcopy(INDEX[reference])
    for key in ['book', 'file', 'ref']: unit.pop(key, None)
    unit['reference'] = reference; unit['text_sha256'] = text_sha(unit['text'])
    if 'continuation_paragraphs' in unit: unit['complete_text_sha256'] = text_sha(complete_text(unit))
    return unit

def prepare():
    progress, head = current_base(); before = load(HERE / 'before-proverbs__verses.json')
    require(not (REPO / ARCHIVE).exists() and not (REPO / ('review-batches/' + RUN + '.json')).exists() and not (REPO / ('proverbs/review-batches/' + RUN + '.json')).exists(), 'Current-run archive already exists; use audit instead of reintegration')
    capture_paths = ['progress.json', 'README.md'] + ['proverbs/' + name for name in ['verses.json', 'source-checks.json', 'RESTORE.md', 'README.md', 'Proverbs.html', 'Proverbs.txt', 'verification.json']]
    original_outputs = {path: (REPO / path).read_bytes() for path in capture_paths}
    require(json.loads(original_outputs['progress.json']) == progress, 'Concurrent progress update at preparation start; retry safely')
    data = deepcopy(before); checks = load(HERE / 'before-proverbs__source-checks.json')
    notes = load(HERE / 'before-proverbs__editorial-notes.json'); plans = packets(); registry = verified_registry()
    frozen_packet_inputs = {name: value for p in plans.values() for name, value in p['frozen_inputs'].items()}
    require(all(digest(HERE / name) == value for name, value in frozen_packet_inputs.items()), 'Final packet bytes changed during source verification')
    pins = {x['book']: x for x in registry['books']}
    def source(book):
        item = pins[book]
        return {'repository': SOURCE_REPO, 'commit': PIN, 'path': item['path'], 'blob_sha': item['blob_sha'], 'url': f'https://github.com/{SOURCE_REPO}/blob/{PIN}/{item["path"]}'}
    units = {v['reference']: v for v in flat(data)}; old_units = {v['reference']: v for v in flat(before)}
    old_checks = deepcopy(checks); all_rows = []; deferred = []; candidates = []; hints = []
    for stem, p in plans.items():
        a = p['author']; all_rows.extend(p['rows'])
        for raw_hint in p['cases']['unread_hints']:
            hint = deepcopy(raw_hint); hint.update(source_and_target_text_read=False, completed_source_credit=0, completed_pair_credit=0, review_batch=RUN)
            hints.append(hint)
        for row in p['rows']:
            ref = row['source_reference']; unit = units[ref]; original_unit = INDEX[ref]
            require(old_units[ref]['status'] == 'pending' and not old_units[ref]['cross_references'], 'Revisiting a historical source')
            for key, value in original_unit.items():
                if key not in {'book', 'file', 'ref'}: require(unit.get(key) == value, 'Source native field differs: ' + ref + '/' + key)
            target_units = [evidence(k) for k in keys(row['target'])]
            edge = {'id': slug(ref) + '__' + slug(row['target']), 'target': row['target'], 'verdict': 'supported', 'relationship': row['relationship'], 'rationale': row['rationale'], 'reviewed': DATE, 'reviewer': a['reviewer'], 'review_batch': RUN, 'source_text_sha256': text_sha(unit['text']), 'target_source': source(INDEX[target_units[0]['reference']]['book']), 'target_verses': target_units, 'target_passage_sha256': text_sha('\n'.join(v['reference'] + ' ' + v['text'] for v in target_units)), 'destination_anchor_check': 'not performed; reference resolves to saved source records'}
            if unit.get('continuation_paragraphs'): edge['source_complete_text_sha256'] = text_sha(complete_text(unit))
            if any(v.get('continuation_paragraphs') for v in target_units): edge['target_passage_complete_sha256'] = text_sha('\n'.join(v['reference'] + ' ' + complete_text(v) for v in target_units))
            unit['cross_references'].append(edge); unit['status'] = 'completed'; unit['reviewed'] = DATE
        for kind, collection in [('deferred_source_units', deferred), ('unresolved_candidates', candidates)]:
            for raw in p['cases'][kind]:
                case = deepcopy(raw); case.update(source_snapshot=deepcopy(data['source_snapshot']), source_verse=evidence(case['source_reference']), reviewer=a['reviewer'], reviewed=DATE, review_timezone='America/New_York', review_batch=RUN, completed_source_credit=0, completed_pair_credit=0)
                if kind == 'unresolved_candidates':
                    kk = keys(case['target']); case.update(target_source=source(INDEX[kk[0]]['book']), target_verses=[evidence(k) for k in kk])
                    case.update(retained=False, identity_resolved=True, source_and_target_text_read=True, evidence_support_status='pending supported relationship; excluded from completion')
                    case['target_passage_sha256'] = text_sha('\n'.join(v['reference'] + ' ' + v['text'] for v in case['target_verses']))
                    if any(v.get('continuation_paragraphs') for v in case['target_verses']): case['target_passage_complete_sha256'] = text_sha('\n'.join(v['reference'] + ' ' + complete_text(v) for v in case['target_verses']))
                else: case.update(target=None, source_unit_read=True)
                collection.append(case)
    cohort = {ref for p in plans.values() for ref in p['cohort']}; supported = {r['source_reference'] for r in all_rows}
    for chapter, old in zip(data['chapters'], before['chapters']):
        require({k:v for k,v in chapter.items() if k not in {'status','verses'}} == {k:v for k,v in old.items() if k not in {'status','verses'}}, 'Source section metadata changed')
        for unit, prior in zip(chapter['verses'], old['verses']):
            if unit['reference'] not in supported: require(unit == prior, 'Earlier or pending source object changed')
            else: require({k:v for k,v in unit.items() if k not in {'status','cross_references','reviewed'}} == {k:v for k,v in prior.items() if k not in {'status','cross_references','reviewed'}}, 'Source native fields changed')
        chapter['status'] = 'completed' if all(v['status'] == 'completed' for v in chapter['verses']) else 'pending'
    checks.setdefault('deferred_source_units', []).extend(deferred); checks.setdefault('unresolved_candidates', []).extend(candidates)
    all_units = flat(data); done = [v for v in all_units if v['status'] == 'completed']; edges = [e for v in done for e in v['cross_references']]
    pending = [v for v in all_units if v['status'] != 'completed']; drefs = {c['source_reference'] for c in checks['deferred_source_units']}
    unread = [v for v in pending if v['reference'] not in drefs]
    previously_read = {v['reference'] for v in flat(before) if v['status'] == 'completed'} | {c['source_reference'] for c in old_checks['deferred_source_units']}
    never_before = [v['reference'] for v in flat(before) if v['reference'] not in previously_read]
    require(cohort == set(never_before[:572]), 'New cohort is not the exact next source-order prefix')
    require(unread[0]['reference'] == 'Proverbs 24:1', 'Unexpected next never-reviewed source')
    nextnew = {'book': 'Proverbs', 'chapter': 24, 'reference': unread[0]['reference'], 'source_id': unread[0]['id']}
    data.update(date=DATE, completed_source_verses=len(done), completed_cross_references=len(edges), completed_chapters=completed_chapter_numbers(data), completed_source_sections=completed_source_sections(data), next_reference=pending[0]['reference'], next_unreviewed_reference=unread[0]['reference'], review_status='initial_curated_pass_in_progress')
    checks.update(date=DATE, next_unreviewed_reference=unread[0]['reference'], checked_scope={'source_passage': 'Proverbs 1:1-23:35', 'source_passage_is_review_scope': True, 'source_units_read': len(previously_read | cohort), 'source_verse_units': len(done), 'deferred_source_units': len(drefs), 'retained_pairs': len(edges), 'distinct_target_verse_units': len({t['reference'] for e in edges for t in e['target_verses']})})
    # Preserve source registry order and historical records, appending only new pins.
    existing = {s['path']: s for s in checks['sources']}
    for book in sorted(pins):
        src = source(book)
        if src['path'] in existing: require(existing[src['path']] == src, 'Historical source pin differs')
        else: checks['sources'].append(src)
    checks['pending'] = ['First pending source unit: ' + pending[0]['reference'], f'{len(previously_read | cohort)} of 939 original source units have been read; {len(unread)} are never reviewed. Deferred source units remain incomplete.', 'Next never-reviewed source: ' + nextnew['reference'] + '.', 'Read but deferred source units: ' + ', '.join(c['source_reference'] for c in checks['deferred_source_units']), 'Independent specialist review', 'Live destination anchors and reader display checks'] + ['Target evidence pending: ' + c['source_reference'] + ' / ' + c['target'] for c in checks['unresolved_candidates']]
    checks['review_batches'].append({'run_id': RUN, 'records': 'review-batches/' + RUN + '.json', 'new_source_verses': len(supported), 'new_pairs': len(all_rows), 'source_units_read': 572, 'first_reviewed_source_units': 572, 'revisited_source_units_read': 0, 'resolved_source_deferrals': 0, 'deferred_source_units': len(deferred), 'unresolved_retained_cases': 0})
    book_record = next(b for b in progress['books'] if b['book'] == 'Proverbs')
    book_record.update(completed_source_verses=len(done), completed_cross_references=len(edges), completed_chapters=data['completed_chapters'], completed_source_sections=data['completed_source_sections'], next_reference=data['next_reference'], next_unreviewed_reference=data['next_unreviewed_reference'], completed_verse_ranges=[c['verses'][0]['reference'] + '-' + c['verses'][-1]['reference'].rsplit(':', 1)[-1] for c in data['chapters'] if c['status'] == 'completed'])
    progress.update(updated=DATE, updated_at_utc=datetime.now(timezone.utc).isoformat(), completed_source_verses=sum(b['completed_source_verses'] for b in progress['books']), completed_cross_references=sum(b['completed_cross_references'] for b in progress['books']), completed_chapters=sum(len(b.get('completed_chapters', [])) for b in progress['books']), next_unreviewed=nextnew)
    require(progress['next']['reference'] == '1 Chronicles 1:24', 'Earliest pending changed')
    oldp = load(HERE / 'before-progress.json'); newchapters = [c for c in data['completed_chapters'] if c not in before['completed_chapters']]
    last = oldp['runs'][-1]
    result = {'book': 'Proverbs', 'source_range': 'Proverbs 5:1-23:35', 'source_range_is_review_scope': True, 'source_units_read': 572, 'first_reviewed_source_units': 572, 'revisited_source_units_read': 0, 'new_completed_revisited_sources': 0, 'distinct_source_verses': len(supported), 'new_completed_pairs': len(all_rows), 'new_deferred_source_units_count': len(deferred), 'total_deferred_source_units_count': len(drefs), 'completed_chapters': data['completed_chapters'], 'new_completed_chapters': newchapters, 'reviewed_dates': [DATE], 'book_initial_curated_pass_complete': False, 'all_original_source_units_read': False, 'next_reference': data['next_reference'], 'next_unreviewed_reference': data['next_unreviewed_reference']}
    run = {**result, 'run_id': RUN, 'date': DATE, 'synchronized': DATE, 'book_results': [result], 'resolved_source_deferrals_count': 0, 'total_deferred_source_units_count': last['total_deferred_source_units_count'] + len(deferred), 'hourly_target': 500, 'target_met': len(all_rows) >= 500, 'target_shortfall': max(0, 500-len(all_rows)), 'target_excess': max(0, len(all_rows)-500), 'unresolved_retained_cases': 0, 'new_unresolved_candidate_count': len(candidates), 'known_pending_target_candidate_count': last['known_pending_target_candidate_count'] + len(candidates), 'review_record': 'review-batches/' + RUN + '.json', 'next_reference': progress['next']['reference'], 'next_unreviewed_reference': nextnew['reference'], 'inventories_added': [], 'review_base_commit': BASE}
    run.pop('book'); progress['runs'].append(run)
    require(progress['runs'][:-1] == oldp['runs'] and len(progress['runs']) == 39, 'Historical run mutation')
    archive_files = ['run-config.json', 'incremental.py', 'passages.py', 'source-registry.json'] + registry['files']
    for stem, p in plans.items():
        archive_files += [stem + '.tsv', stem + '-cases.json', p['author_file'].name, p['peer_file'].name]
        for r in [p['author'], p['peer']]:
            for field in ['reread_evidence', 'reading_log']:
                record = r.get(field)
                if isinstance(record, dict) and 'file' in record and record['file'] not in archive_files: archive_files.append(record['file'])
    require(len(archive_files) == len(set(archive_files)), 'Duplicate archive filename')
    require(all(Path(name).name == name for name in archive_files), 'Archive filename must be a plain current-run filename')
    require(all(digest(HERE / name) == value for name, value in frozen_packet_inputs.items()), 'Parsed author/peer evidence changed before archive creation')
    batch = {**run, 'source_repository': SOURCE_REPO, 'source_commit': PIN, 'reviewed': DATE, 'completion_definition': data['completion_definition'], 'review_receipts': [p['author'] for p in plans.values()], 'peer_review_receipts': [p['peer'] for p in plans.values()], 'deferred_source_units': deferred, 'unresolved_candidates': candidates, 'unread_hints': hints, 'unresolved_retained_cases': [], 'unread_hints_completion_credit': 0, 'input_archive': ARCHIVE, 'archived_input_files': [{'file': name, 'sha256': frozen_packet_inputs.get(name, digest(HERE / name)), 'completion_credit': 0} for name in archive_files], 'historical_evidence': {'baseline_commit': BASE, 'prior_run_count': 38, 'preservation': 'Existing historical records and archives remain immutable Git objects; no prior helper chain is imported or repackaged.'}, 'remaining_checks': ['Independent specialist review', 'Live destination anchors and display verification'], 'chapter_pair_counts': dict(Counter(r['source_reference'].rsplit(' ',1)[-1].split(':')[0] for r in all_rows))}
    outputs = {'progress.json': encoded(progress), 'proverbs/verses.json': encoded(data), 'proverbs/source-checks.json': encoded(checks), 'review-batches/' + RUN + '.json': encoded(batch), 'proverbs/review-batches/' + RUN + '.json': encoded({**batch, **result, 'overall_review_record': '../../review-batches/' + RUN + '.json'})}
    for item in batch['archived_input_files']:
        raw = (HERE / item['file']).read_bytes()
        require(sha(raw) == item['sha256'], 'Review input changed while archiving: ' + item['file'])
        outputs[ARCHIVE + item['file']] = raw
    outputs[ARCHIVE + '.gitattributes'] = b'* -text whitespace=cr-at-eol\n'
    restore = original_outputs['proverbs/RESTORE.md'].decode('utf-8').replace('\r\n', '\n').split('\n## Pending source review recovery\n')[0]
    restore += f'\n\n## Pending source review recovery\n\n939 original units in 31 native chapters and 34 original source sections remain unchanged. {len(previously_read | cohort)} units have been read: {len(done)} completed sources and {len(edges)} retained pairs; {len(unread)} units have never been reviewed. Read source deferrals earn zero completion credit: ' + ', '.join(c['source_reference'] for c in checks['deferred_source_units']) + f'. First pending source: **{data["next_reference"]}**. Next never-reviewed source: **{nextnew["reference"]}**. Root earliest pending remains **1 Chronicles 1:24**. Preserve every original section, native field, prior completed object, deferred case, candidate and historical run.\n'
    outputs['proverbs/RESTORE.md'] = restore.encode('utf-8')
    # Render only this book with the unchanged production renderer, entirely in scratch.
    stage = HERE / ('prepared-' + uuid.uuid4().hex); (stage / 'proverbs').mkdir(parents=True)
    for path, raw in outputs.items():
        if path in {'progress.json', 'proverbs/verses.json', 'proverbs/source-checks.json'}: (stage / path).write_bytes(raw)
    (stage / 'proverbs/README.md').write_bytes(original_outputs['proverbs/README.md'])
    render = module('current_renderer', REPO / 'scripts/render_books.py'); render.ROOT = stage
    style = re.search(r'<style>(.*?)</style>', (REPO / 'genesis/Genesis.html').read_text(encoding='utf-8'), re.S).group(1)
    render.render_book(book_record, progress, style)
    for name in ['Proverbs.html', 'Proverbs.txt', 'README.md']: outputs['proverbs/' + name] = (stage / 'proverbs' / name).read_bytes()
    # Keep unrelated root README text byte-for-byte except explicit OT summary fields.
    readme = original_outputs['README.md'].decode('utf-8').replace('\r\n', '\n')
    line = '- [Proverbs — 31 chapters in 34 source sections](proverbs/README.md): initial curated pass in progress; latest completed unit ' + done[-1]['reference'] + f'; **{len(done)} source verses, {len(edges)} matching cross-reference pairs**.'
    readme = re.sub(r'^- \[Proverbs[^\n]+', lambda _: line, readme, flags=re.M)
    readme = readme.replace('Proverbs has 939 inventoried source units, of which 119 are completed.', f'Proverbs has 939 inventoried source units, of which {len(done):,} are completed.')
    readme = readme.replace('**Next new source review: Proverbs 5:1.**', '**Next new source review: ' + nextnew['reference'] + '.**')
    readme = re.sub(r'^Latest saved review: [^\n]+', lambda _: f'Latest saved review: {DATE}, **{len(all_rows)} new pairs across {len(supported)} source verses**. Hourly target: 500; shortfall: {max(0,500-len(all_rows))}. [Review record](review-batches/{RUN}.json).', readme, flags=re.M)
    outputs['README.md'] = readme.encode('utf-8')
    # Continuation prose is the only allowed alteration outside Proverbs/root summaries.
    oldnew = oldp['next_unreviewed']['reference']
    for b in progress['books']:
        if b['book'] == 'Proverbs' or b['status'] == 'completed': continue
        source_file = REPO / b['records'] / 'verses.json'
        related_names = ['source-checks.json', 'RESTORE.md', 'README.md']
        if source_file.exists():
            related_book = load(source_file)
            related_names += [related_book['readable_text'], related_book['readable_html']]
        for name in related_names:
            path = b['records'] + name; file = REPO / path
            if not file.exists(): continue
            raw = file.read_bytes(); original_outputs[path] = raw; text = raw.decode('utf-8')
            for prefix, suffix in [('Next new source review: ', '.'), ('Next never-reviewed source: ', '.'), ('The next new source review is **', '**'), ('separate next_unreviewed at **', '**')]:
                text = text.replace(prefix + oldnew + suffix, prefix + nextnew['reference'] + suffix)
            if text.encode('utf-8') != raw: outputs[path] = text.encode('utf-8')
    # Path.write_text in the production renderer emits CRLF on Windows.
    # Normalize rendered text before comparing complete bodies and source lines.
    outputs = {path: raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n', b'\n') for path, raw in outputs.items()}
    audit_objects(data, progress, checks, outputs)
    verification = load(HERE / 'before-proverbs__verification.json')
    verification.update(checked_at_utc=datetime.now(timezone.utc).isoformat(), completed_source_verses=len(done), completed_chapters=data['completed_chapters'], completed_cross_references=len(edges), unique_pair_ids=len(edges), validation_scope='Incremental preservation and complete new evidence checks; production chapter_structure and HTML parser reused. Full production validator is also required after apply.')
    outputs['proverbs/verification.json'] = encoded(verification)
    # Working checkouts use CRLF; canonical non-archive Git content uses LF.
    # The archive's -text attribute preserves exact receipt and raw-source bytes.
    outputs = {path: raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n', b'\n') for path, raw in outputs.items()}
    summary = {'run_id': RUN, 'source_units_read': 572, 'new_completed_sources': len(supported), 'new_pairs': len(all_rows), 'new_deferred_sources': len(deferred), 'new_candidates': len(candidates), 'unread_hints': len(hints), 'completed_source_verses': progress['completed_source_verses'], 'completed_pairs': progress['completed_cross_references'], 'completed_chapters': progress['completed_chapters'], 'next': progress['next'], 'next_unreviewed': nextnew, 'output_files': len(outputs), 'archive_files': len(archive_files), 'review_base_commit': BASE, 'observed_head': head, 'staging_directory': str(stage)}
    for path, raw in outputs.items():
        out = safe_path(stage, path); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(raw)
    for item in batch['archived_input_files']: require(digest(HERE / item['file']) == item['sha256'], 'Review input changed before preflight completed')
    for path in outputs:
        current = (REPO / path).read_bytes() if (REPO / path).exists() else None
        require(current == original_outputs.get(path), 'Output changed or appeared during preparation: ' + path)
    manifest = {'run_id': RUN, 'stage': str(stage), 'summary': summary, 'frozen_inputs': batch['archived_input_files'], 'outputs': [{'path': path, 'sha256': sha(raw), 'before_sha256': sha(original_outputs[path]) if path in original_outputs else None} for path, raw in outputs.items()]}
    (HERE / 'prepared-manifest.json').write_bytes(encoded(manifest)); return outputs, manifest

def audit_objects(data, progress, checks, outputs=None):
    before = load(HERE / 'before-proverbs__verses.json'); oldp = load(HERE / 'before-progress.json'); oldc = load(HERE / 'before-proverbs__source-checks.json')
    require(len(data['chapters']) == 34 and len(flat(data)) == 939 and len(chapter_units(data)) == 31, 'Inventory shape changed')
    require(progress['runs'][:-1] == oldp['runs'], 'Prior runs changed')
    require(checks['deferred_source_units'][:len(oldc['deferred_source_units'])] == oldc['deferred_source_units'] and checks['unresolved_candidates'][:len(oldc['unresolved_candidates'])] == oldc['unresolved_candidates'], 'Prior cases changed')
    for a, b in zip(oldp['books'], progress['books']):
        if a['book'] != 'Proverbs': require(a == b, 'Unrelated book record changed')
    count = 0
    for old, new in zip(flat(before), flat(data)):
        require(old['reference'] == new['reference'], 'Native ordering changed')
        if old['status'] == 'completed': require(old == new, 'Previously completed object changed')
        require({k:v for k,v in old.items() if k not in {'cross_references','status','reviewed'}} == {k:v for k,v in new.items() if k not in {'cross_references','status','reviewed'}}, 'Native source field changed')
        for edge in new['cross_references']:
            if edge.get('review_batch') != RUN: continue
            target = [evidence(k) for k in keys(edge['target'])]
            require(edge['target_verses'] == target, 'Complete target/native evidence differs')
            require(edge['source_text_sha256'] == text_sha(new['text']), 'Source hash mismatch')
            require(edge['target_passage_sha256'] == text_sha('\n'.join(t['reference'] + ' ' + t['text'] for t in target)), 'Target hash mismatch')
            count += 1
    require(count == progress['runs'][-1]['new_completed_pairs'], 'New edge count mismatch')
    require(data['completed_chapters'] == completed_chapter_numbers(data) and data['completed_source_sections'] == completed_source_sections(data), 'Native chapter aggregation mismatch')
    completed = [v for v in flat(data) if v['status'] == 'completed']
    edges = [e for v in completed for e in v['cross_references']]
    require(len({e['id'] for e in edges}) == len(edges), 'Duplicate pair ID')
    require((len(completed), len(edges)) == (data['completed_source_verses'], data['completed_cross_references']), 'Book totals mismatch')
    require(progress['completed_source_verses'] == sum(b['completed_source_verses'] for b in progress['books']) and progress['completed_cross_references'] == sum(b['completed_cross_references'] for b in progress['books']), 'Root totals mismatch')
    if outputs:
        validator = module('current_validator', REPO / 'scripts/validate.py'); parser = validator.Anchors(); parser.feed(outputs['proverbs/Proverbs.html'].decode('utf-8'))
        done = [v for v in flat(data) if v['status'] == 'completed']; edges = [e for v in done for e in v['cross_references']]
        require(parser.scripture == [complete_text(v) for v in done], 'Rendered complete source text differs')
        require(parser.target_scripture == [t['reference'] + ' ' + complete_text(t) for e in edges for t in e['target_verses']], 'Rendered complete target text differs')
        require(Counter(parser.ids) == Counter(v['id'] for v in done) and parser.details == len(edges), 'Rendered anchors/pair count differs')
        if 'proverbs/Proverbs.txt' in outputs:
            text = outputs['proverbs/Proverbs.txt'].decode('utf-8')
            for unit in done: require(unit['reference'] + '\n' + complete_text(unit) + '\n' in text, 'Readable complete source text differs')
    return {'result': 'passed', 'new_pairs_checked': count, 'historical_runs_preserved': 38, 'inventory_units_preserved': 939, 'native_chapters': 31, 'source_sections': 34, 'completion_credit': 0}

def apply():
    outputs, manifest = prepare(); current_base()
    for item in manifest['frozen_inputs']: require(digest(HERE / item['file']) == item['sha256'], 'Review input changed before apply')
    journal_dir = HERE / ('transaction-' + uuid.uuid4().hex); journal_dir.mkdir()
    journal = {'run_id': RUN, 'state': 'preparing', 'entries': [], 'completion_credit': 0, 'recovery_rule': 'Compare every current file against its saved before/after bytes regardless of recorded entry state. Restore only when current equals after. Preserve any other bytes as concurrent edits. Remove new files only when current equals after. Never delete directories recursively.'}
    for index, item in enumerate(manifest['outputs']):
        path = safe_path(REPO, item['path']); old = path.read_bytes() if path.exists() else None
        require((sha(old) if old is not None else None) == item['before_sha256'], 'Output changed during preparation')
        if old is not None: (journal_dir / f'{index}.before').write_bytes(old)
        (journal_dir / f'{index}.after').write_bytes(outputs[item['path']])
        journal['entries'].append({**item, 'index': index, 'existed': old is not None, 'state': 'prepared'})
    def save():
        next_path = journal_dir / 'journal.next.json'
        with next_path.open('wb') as stream: stream.write(encoded(journal)); stream.flush(); os.fsync(stream.fileno())
        os.replace(next_path, journal_dir / 'journal.json')
    save(); replaced = []; created_temporaries = set()
    try:
        journal['state'] = 'applying'; save()
        for item in journal['entries']:
            path = safe_path(REPO, item['path']); now = path.read_bytes() if path.exists() else None
            require((sha(now) if now is not None else None) == item['before_sha256'], 'Concurrent output change: ' + item['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.parent / ('.codex-' + uuid.uuid4().hex + '.tmp')
            item['temporary_path'] = temp.relative_to(REPO).as_posix(); save()
            with temp.open('xb') as stream:
                created_temporaries.add(item['temporary_path']); stream.write(outputs[item['path']]); stream.flush(); os.fsync(stream.fileno())
            require((digest(path) if path.exists() else None) == item['before_sha256'], 'Concurrent write boundary change')
            os.replace(temp, path); replaced.append(item); item['state'] = 'applied'; save()
        journal['state'] = 'applied'; save()
    except BaseException:
        journal['state'] = 'rolling_back'; journal['conflicts'] = []
        for item in reversed(replaced):
            restore_temp = None
            try:
                path = safe_path(REPO, item['path'])
                require(path.exists() and digest(path) == item['sha256'], 'Concurrent bytes before rollback')
                if item['existed']:
                    restore_temp = path.parent / ('.codex-' + uuid.uuid4().hex + '.restore')
                    original_raw = (journal_dir / f'{item["index"]}.before').read_bytes()
                    with restore_temp.open('xb') as stream: stream.write(original_raw); stream.flush(); os.fsync(stream.fileno())
                    # A separate NT writer may update progress while the restore
                    # temporary is written. Preserve those concurrent bytes.
                    path = safe_path(REPO, item['path'])
                    require(path.exists() and digest(path) == item['sha256'], 'Concurrent bytes at rollback replacement boundary')
                    os.replace(restore_temp, path)
                else:
                    path = safe_path(REPO, item['path'])
                    require(path.exists() and digest(path) == item['sha256'], 'Concurrent bytes at rollback removal boundary')
                    path.unlink()
                item['state'] = 'rolled_back'
            except BaseException as rollback_error:
                item['rollback_error'] = repr(rollback_error); journal['conflicts'].append(item['path'])
            finally:
                if restore_temp is not None and restore_temp.exists():
                    try:
                        expected = (journal_dir / f'{item["index"]}.before').read_bytes(); raw = restore_temp.read_bytes()
                        require(raw == expected[:len(raw)], 'Unexpected restore temporary bytes')
                        restore_temp.unlink()
                    except BaseException as cleanup_error:
                        journal['conflicts'].append(str(restore_temp)); item['restore_cleanup_error'] = repr(cleanup_error)
        for item in journal['entries']:
            if item.get('temporary_path') not in created_temporaries: continue
            temporary = safe_path(REPO, item['temporary_path'])
            if temporary.exists():
                raw = temporary.read_bytes(); expected = outputs[item['path']]
                if raw == expected[:len(raw)]: temporary.unlink()
                else: journal['conflicts'].append(item['temporary_path'])
        journal['state'] = 'rollback_conflict' if journal['conflicts'] else 'rolled_back'; save(); raise
    return {**manifest['summary'], 'applied': True, 'journal': str(journal_dir / 'journal.json')}

def capture_maintenance(manifest):
    """Freeze the exact global renderer/--write-verification maintenance root ran.

    This checks fresh production-schema receipts, preserves old Scripture bodies,
    and records derived output bytes. It does not claim to invoke those commands.
    """
    progress = load(REPO / 'progress.json'); allowed = {'README.md'}
    changed = set(git('diff', '--name-only', BASE).decode().splitlines())
    parser_module = module('maintenance_parser', REPO / 'scripts/validate.py')
    run_start = datetime.strptime(RUN, '%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    old_next = load(HERE / 'before-progress.json')['next_unreviewed']['reference']; new_next = progress['next_unreviewed']['reference']
    verified_books = []
    for record in progress['books']:
        folder = record['records']; path = REPO / folder / 'verses.json'
        if not path.exists(): continue
        data = load(path); verification_path = folder + 'verification.json'
        actual = load(REPO / verification_path); expected = json.loads(original(verification_path))
        require(datetime.fromisoformat(actual['checked_at_utc']) >= run_start, 'Run full scripts/validate.py --write-verification before audit: ' + record['book'])
        actual_without_time = {k:v for k,v in actual.items() if k != 'checked_at_utc'}
        expected.pop('checked_at_utc'); expected.update(completed_source_verses=data['completed_source_verses'], completed_chapters=data['completed_chapters'], completed_cross_references=data['completed_cross_references'], unique_pair_ids=data['completed_cross_references'])
        require(actual_without_time == expected, 'Global production verification schema/counts differ: ' + record['book'])
        allowed.update(folder + name for name in ['README.md', data['readable_html'], data['readable_text'], 'verification.json'])
        verified_books.append(record['book'])
        if record['book'] == 'Proverbs': continue
        html_path = folder + data['readable_html']
        if html_path in changed:
            old_parser = parser_module.Anchors(); new_parser = parser_module.Anchors()
            old_parser.feed(original(html_path).decode('utf-8').replace('\r\n','\n')); new_parser.feed((REPO / html_path).read_text(encoding='utf-8'))
            for field in ['ids', 'details', 'scripture', 'target_scripture']: require(getattr(old_parser,field) == getattr(new_parser,field), 'Maintenance changed historical HTML Scripture: ' + html_path)
        text_path = folder + data['readable_text']
        if text_path in changed:
            old_text = original(text_path).decode('utf-8').replace('\r\n','\n')
            for prefix in ['Next new source review: ', 'Next never-reviewed source: ']: old_text = old_text.replace(prefix + old_next + '.', prefix + new_next + '.')
            require((REPO / text_path).read_text(encoding='utf-8') == old_text, 'Maintenance changed historical plain text beyond continuation: ' + text_path)
    existing = {item['path']: item for item in manifest['outputs']}
    # Immutable structured data and archives must still match before extending
    # the allowed maintenance scope. progress permits its separate NT pointer.
    for path, item in existing.items():
        if path in allowed or path == 'progress.json': continue
        raw = (REPO / path).read_bytes(); raw = raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n',b'\n')
        require(sha(raw) == item['sha256'], 'Protected output changed before maintenance capture: ' + path)
    captured = sorted((changed | set(existing)) & allowed)
    for path in captured:
        raw = (REPO / path).read_bytes().replace(b'\r\n', b'\n')
        item = existing.get(path, {'path': path, 'maintenance_only': True})
        item['sha256'] = sha(raw); existing[path] = item
        stage_path = safe_path(Path(manifest['stage']), path); stage_path.parent.mkdir(parents=True, exist_ok=True); stage_path.write_bytes(raw)
    manifest['outputs'] = list(existing.values())
    manifest['maintenance'] = {'required_external_commands': ['python scripts/render_genesis.py', 'python scripts/validate.py --write-verification'], 'renderer_compatibility_entrypoint': 'render_genesis.py calls render_books.main', 'fresh_production_verification_books': verified_books, 'historical_scripture_bodies_preserved': True, 'captured_derived_files': captured, 'completion_credit': 0}
    (HERE / 'prepared-manifest.json').write_bytes(encoded(manifest)); return manifest

def readback(ref=None):
    manifest = load(HERE / 'prepared-manifest.json')
    if not ref: manifest = capture_maintenance(manifest)
    def get(path):
        raw = original(path, ref) if ref else (REPO / path).read_bytes()
        return raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n', b'\n')
    data, progress, checks = [json.loads(get(p)) for p in ['proverbs/verses.json', 'progress.json', 'proverbs/source-checks.json']]
    expected_progress = load(Path(manifest['stage']) / 'progress.json')
    require(without_nt(progress) == without_nt(expected_progress), 'Readback OT progress differs')
    for item in manifest['outputs']:
        if item['path'] == 'progress.json': continue
        require(sha(get(item['path'])) == item['sha256'], 'Readback output differs: ' + item['path'])
    inventory = get('proverbs/inventory.json')
    require(inventory.replace(b'\r\n', b'\n') == original('proverbs/inventory.json').replace(b'\r\n', b'\n'), 'Inventory blob changed')
    allowed = {i['path'] for i in manifest['outputs']}
    changed = git('diff', '--name-only', BASE, ref if ref else 'HEAD').decode().splitlines()
    if not ref: changed += git('diff', '--name-only', 'HEAD').decode().splitlines()
    require(all(p in allowed or is_nt(p) for p in changed), 'Unrelated historical file changed: ' + ', '.join(p for p in changed if p not in allowed and not is_nt(p)))
    result = audit_objects(data, progress, checks, {'proverbs/Proverbs.html': get('proverbs/Proverbs.html'), 'proverbs/Proverbs.txt': get('proverbs/Proverbs.txt')})
    result.update(ref=ref or 'working tree', inventory_git_blob_sha=blob(original('proverbs/inventory.json')), scope='Only this run outputs and changed paths checked; prior evidence preserved by Git object identity, not rereviewed.')
    (HERE / ('published-readback.json' if ref else 'preservation-audit.json')).write_bytes(encoded(result)); return result

def publication_check(ref):
    """Read-only check for a normal concurrent NT merge; never resets or reapplies review."""
    changed = git('diff', '--name-only', BASE, ref).decode().splitlines()
    require(all(is_nt(p) or p == 'progress.json' for p in changed), 'Remote contains concurrent OT changes')
    remote = json.loads(original('progress.json', ref)); before = load(HERE / 'before-progress.json')
    require(without_nt(remote) == without_nt(before), 'Remote OT objects differ from review baseline')
    result = {'remote_ref': ref, 'remote_commit': git('rev-parse', ref).decode().strip(), 'review_base_commit': BASE, 'only_independent_nt_changes': True, 'remote_nt_pointer': remote.get('new_testament_tracker'), 'merge_instruction': 'Perform a normal Git merge. If only progress.json conflicts, preserve the complete local OT object and replace only new_testament_tracker with remote_nt_pointer. Do not reset or regenerate the semantic batch.', 'completion_credit': 0}
    (HERE / 'publication-check.json').write_bytes(encoded(result)); return result

def main():
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    for arg in ['baseline', 'required-sources', 'refresh-sources', 'preflight', 'apply', 'audit-local']: group.add_argument('--' + arg, action='store_true')
    group.add_argument('--readback'); group.add_argument('--publication-check'); args = parser.parse_args()
    if args.baseline: result = baseline()
    elif args.required_sources: result = required_sources()
    elif args.refresh_sources: result = refresh_sources()
    elif args.preflight: result = {'preflight_only': True, **prepare()[1]['summary']}
    elif args.apply: result = apply()
    elif args.audit_local: result = readback()
    elif args.readback: result = readback(args.readback)
    else: result = publication_check(args.publication_check)
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main()
