"""Current existing-Sirach append batch only. All preparation is scratch; --apply is explicit.

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
PLAN = json.loads((HERE / 'review-plan.json').read_text(encoding='utf-8'))
STEMS = {p['stem']:p['book'] for p in PLAN['packets']}
REVIEW_BOOKS = CONFIG['source_book_sequence']
SOURCE_REPO = 'Dotty777/Saints-Translation'
ARCHIVE = re.sub('[^a-z0-9]+','-',REVIEW_BOOKS[0].lower()).strip('-') + '/review-batches/' + RUN + '/'
ALLOWED_NT = {'scripts/render_new_testament.py', 'scripts/validate_new_testament.py'}
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(REPO / 'scripts'))
from passages import INDEX, keys, complete_text
from chapter_structure import chapter_units, completed_chapter_numbers, completed_source_sections
from functools import lru_cache

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
def newline_only_root_change(path, ref=None):
    if path not in {'canon.json','README.md'}: return False
    raw=original(path,ref) if ref else (REPO/path).read_bytes()
    return raw.replace(b'\r\n',b'\n')==original(path).replace(b'\r\n',b'\n')
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

@lru_cache(maxsize=1)
def baseline_files():
    return set(git('ls-tree','-r','--name-only',BASE).decode().splitlines())

@lru_cache(maxsize=1)
def baseline_records():
    return [b for b in load(HERE/'before-progress.json')['books'] if b['records']+'verses.json' in baseline_files()]

def protected_book_paths():
    return [b['records']+name+'.json' for b in baseline_records() for name in ['verses','source-checks','inventory','editorial-notes','verification'] if b['records']+name+'.json' in baseline_files()]

def baseline():
    identities={}
    for path in ['canon.json','progress.json']+[slug(b)+'/'+n+'.json' for b in REVIEW_BOOKS for n in ['verses','source-checks','inventory','editorial-notes','verification']]:
        raw=original(path);saved=HERE/('before-'+path.replace('/','__'))
        require(json.loads(raw)==load(saved),'Before snapshot differs: '+path)
        identities[path]={'git_blob_sha':blob(raw),'snapshot_sha256':digest(saved)}
    p=load(HERE/'before-progress.json')
    require(not any(r.get('run_id')==RUN for r in p['runs']),'Current run already exists in baseline')
    require((PLAN['run_id'],PLAN['baseline_commit'],PLAN['source_commit'])==(RUN,BASE,PIN),'Review plan identity')
    require(PLAN['source_book_sequence']==REVIEW_BOOKS and len(STEMS)==len(PLAN['packets']),'Review plan book sequence or duplicate stem')
    require(list(dict.fromkeys(STEMS.values()))==REVIEW_BOOKS,'Packet books must follow the canonical source sequence')
    order=[b['book'] for b in p['books']];i=order.index(p['next_unreviewed']['book'])
    require(REVIEW_BOOKS==order[i:i+len(REVIEW_BOOKS)],'Review plan must follow the exact canonical continuation')
    require(all(b in REVIEW_BOOKS for b in STEMS.values()),'Packet outside existing source books')
    require(all(slug(b)+'/verses.json' in baseline_files() for b in REVIEW_BOOKS),'Existing-book append requires baseline records')
    for book in REVIEW_BOOKS: existing_book(book)
    return {'run_id':RUN,'baseline_commit':BASE,'source_commit':PIN,'historical_runs':len(p['runs']),'existing_book_records':len(baseline_records()),'completed_source_verses':p['completed_source_verses'],'completed_pairs':p['completed_cross_references'],'files':identities,'completion_credit':0}

def existing_book(book):
    """Read the existing pinned book; never construct or bootstrap a new inventory."""
    require(book in REVIEW_BOOKS,'Existing book outside this run')
    folder=slug(book)+'/';data=load(HERE/('before-'+folder.replace('/','__')+'verses.json'))
    require(data==json.loads(original(folder+'verses.json')),'Existing book differs from exact review baseline')
    require(data['source_snapshot']['commit']==PIN,'Existing book uses a different source commit')
    original_source=load(CACHE/(slug(book)+'.json'))
    require(data['source_metadata']['original_book_metadata']=={k:v for k,v in original_source.items() if k!='chapters'},'Original book metadata changed')
    require(len(data['chapters'])==len(original_source['chapters']),'Original source section shape changed')
    for before,after in zip(original_source['chapters'],data['chapters']):
        require(after['source_metadata']=={k:v for k,v in before.items() if k!='verses'},'Original chapter metadata changed')
        require([{k:v for k,v in u.items() if k not in {'status','cross_references','reviewed'}} for u in after['verses']]==before['verses'],'Original source units/order changed')
    inv=load(HERE/('before-'+folder.replace('/','__')+'inventory.json'))
    require(inv==json.loads(original(folder+'inventory.json')),'Existing inventory differs from baseline')
    require([(v['reference'],v['id'],text_sha(v['text'])) for v in flat(data)]==[(v['reference'],v['id'],v['text_sha256']) for c in inv['chapters'] for v in c['units']],'Inventory unit declarations differ')
    return data

def existing_checks(book):
    path=slug(book)+'/source-checks.json';value=load(HERE/('before-'+path.replace('/','__')))
    require(value==json.loads(original(path)),'Existing source checks differ from baseline')
    return value

def previously_read_refs(book):
    data=existing_book(book);checks=existing_checks(book)
    refs={v['reference'] for v in flat(data) if v['status']=='completed'}|{d['source_reference'] for d in checks.get('deferred_source_units',[])}
    native=[v['reference'] for v in flat(data)]
    require(set(native[:len(refs)])==refs,'Historical read coverage is not an exact native prefix')
    require(checks['checked_scope']['source_units_read']==len(refs),'Historical read coverage count differs')
    return refs

def available_refs(book):
    old=previously_read_refs(book)
    return [v['reference'] for v in flat(existing_book(book)) if v['reference'] not in old]

def ordered_scope(stem):
    packet=next(p for p in PLAN['packets'] if p['stem']==stem);refs=packet['source_references']
    native=[v['reference'] for v in flat(existing_book(STEMS[stem]))]
    require(refs and len(refs)==len(set(refs)) and all(r in native for r in refs),'Invalid explicit source cohort: '+stem)
    return list(refs)

def native_chapter_map(book):
    return {v['reference']:c['chapter'] for c in existing_book(book)['chapters'] for v in c['verses']}

def native_chapters(book,refs):
    chapter_by_ref=native_chapter_map(book)
    return list(dict.fromkeys(chapter_by_ref[r] for r in refs))

def section_range(section):
    first=section['verses'][0]['reference'];last=section['verses'][-1]['reference']
    return first+'-'+last.rsplit(':',1)[-1] if ':' in first and ':' in last else first+' through '+last


def current_base():
    """Allow an independent NT commit or dirty NT files without rebasing OT work."""
    baseline()
    for book in REVIEW_BOOKS:
        require((REPO/slug(book)/'verses.json').is_file(), 'Existing book is missing: '+book)
    head = git('rev-parse', 'HEAD').decode().strip()
    changed = git('diff', '--name-only', BASE, head).decode().splitlines()
    for path in changed:
        require(is_nt(path) or path == 'progress.json' or newline_only_root_change(path,head), 'Concurrent OT commit: ' + path)
    p = load(REPO / 'progress.json'); before = load(HERE / 'before-progress.json')
    require(without_nt(p) == without_nt(before), 'Current OT progress differs from review baseline')
    dirty = git('diff', '--name-only', 'HEAD').decode().splitlines()
    for path in dirty:
        require(is_nt(path) or path == 'progress.json' or newline_only_root_change(path), 'Concurrent OT working edit: ' + path)
    for path in ['canon.json','scripts/chapter_structure.py','scripts/render_books.py','scripts/validate.py']+protected_book_paths():
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
    for k, value in [('run_id', RUN), ('base_commit', BASE), ('source_commit', PIN), ('source_book', STEMS[stem]), ('reviewed', DATE), ('review_timezone', 'America/New_York')]:
        actual=r.get(k,r.get('baseline_commit') if k=='base_commit' else None)
        require(actual == value, 'Receipt identity ' + path.name + ': ' + k)
        if k=='base_commit' and 'baseline_commit' in r:require(r['baseline_commit']==BASE,'Conflicting receipt baseline aliases')
    cohort = ordered_scope(stem)
    require(r.get('source_references') == cohort, 'Receipt explicit source order: ' + stem)
    require(r.get('source_chapters') == native_chapters(STEMS[stem],cohort), 'Receipt native chapter scope: ' + stem)
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
    for flag in ['all_source_verses_read', 'all_target_passages_read', 'necessary_context_read', 'all_retained_rationales_reread']:
        require(r.get(flag) is True, 'Missing ' + ('peer' if peer else 'author') + ' reading attestation: ' + flag)
    require(path.read_bytes() == captured, 'Receipt changed during validation: ' + path.name)
    return path, r

def packets(require_peers=True):
    result = {}; all_pairs = set()
    for stem, book in STEMS.items():
        packet_paths = [HERE / (stem + '.tsv'), HERE / (stem + '-cases.json'), receipt_path(stem)]
        if require_peers: packet_paths.append(receipt_path(stem, True))
        captured = {p.name: p.read_bytes() for p in packet_paths}
        with io.StringIO(captured[stem + '.tsv'].decode('utf-8-sig'), newline='') as stream:
            reader = csv.DictReader(stream, delimiter='\t')
            require(reader.fieldnames == ['source_reference', 'target', 'relationship', 'rationale'], 'TSV schema: ' + stem)
            rows = list(reader)
        cases = json.loads(captured[stem + '-cases.json'])
        require(set(cases) == {'deferred_source_units', 'unresolved_candidates', 'unread_hints'}, 'Cases schema: ' + stem)
        cohort = ordered_scope(stem)
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
            require(hint.get('source_reference') in cohort and isinstance(hint.get('target'),str) and hint['target'].strip() and isinstance(hint.get('reason'),str) and hint['reason'].strip(),'Unread hint must identify a cohort source, target hint and reason')
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
    for book in REVIEW_BOOKS:
        combined=[ref for stem,p in result.items() if STEMS[stem]==book for ref in p['cohort']]
        native=available_refs(book)
        require(combined==native[:len(combined)] and len(combined)==len(set(combined)),'Book packets must cover the exact disjoint next-unread native prefix: '+book)
    return result

def required_sources(require_peers=False):
    plans = packets(require_peers); books = set(STEMS.values()) | set(REVIEW_BOOKS)
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
        else: raise ValueError('Fresh GitHub plugin identity required: ' + identity_file)
        require((metadata['repository'], metadata['ref'], metadata['path']) == (SOURCE_REPO, PIN, spec['path']), 'Wrong fresh identity: ' + spec['book'])
        require(datetime.fromisoformat(metadata['checked_at_utc'])>=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc),'Source identity predates this run: '+spec['book'])
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
        require(datetime.fromisoformat(identity['checked_at_utc'])>=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc),'Source identity predates this run')
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
    progress, head = current_base(); plans = packets(); registry = verified_registry()
    require(load(HERE/'baseline-proof.json')==baseline(),'Frozen baseline proof changed')
    require((HERE/'production-render_books.py').read_bytes()==original('scripts/render_books.py'),'Production renderer snapshot changed')
    gates=load(HERE/'source-review-gates.json')
    require((gates['run_id'],gates.get('base_commit',gates.get('baseline_commit')),gates['source_commit'])==(RUN,BASE,PIN),'Source review gate identity')
    require([g.get('packet_stem',g.get('stem')) for g in gates['gates']]==list(STEMS),'Source review gate ordering')
    for gate in gates['gates']:
        stem=gate.get('packet_stem',gate.get('stem'));cohort=plans[stem]['cohort']
        require(gate.get('source_book',gate.get('book'))==STEMS[stem],'Source reading gate book differs')
        require(gate['source_units_read_this_run']==len(cohort),'Source reading gate count differs')
        require(gate.get('all_actual_cohort_units_read_in_native_order') is True,'Source cohort reading gate incomplete')
        if 'source_references' in gate:require(gate['source_references']==cohort,'Source gate native order differs')
    require(not (REPO / ARCHIVE).exists(), 'Current run already applied; use audit')
    pins = {x['book']:x for x in registry['books']}; oldp = load(HERE / 'before-progress.json')
    original_outputs = {}; outputs = {}; results = []; datasets = {}; checksets = {}; all_deferred=[]; all_candidates=[]; all_hints=[]
    def source(book):
        x=pins[book]; return {'repository':SOURCE_REPO,'commit':PIN,'path':x['path'],'blob_sha':x['blob_sha'],'url':f'https://github.com/{SOURCE_REPO}/blob/{PIN}/{x["path"]}'}
    def put(path, raw):
        file=safe_path(REPO,path)
        require(not file.exists() or path in baseline_files(),'Untracked or concurrent new output collision: '+path)
        if path not in original_outputs: original_outputs[path]=file.read_bytes() if file.exists() else None
        outputs[path]=raw
    for book in REVIEW_BOOKS:
        folder=slug(book)+'/'; before=existing_book(book); data=deepcopy(before)
        checks=existing_checks(book)
        oldchecks=deepcopy(checks); units={v['reference']:v for v in flat(data)}
        applicable=[(stem,p) for stem,p in plans.items() if STEMS[stem]==book]
        rows=[r for stem,p in applicable for r in p['rows']]; cohort=[r for stem,p in applicable for r in p['cohort']]
        deferred=[]; candidates=[]
        for stem,p in applicable:
            a=p['author']
            for row in p['rows']:
                unit=units[row['source_reference']]
                require(all(e.get('review_batch')==RUN for e in unit['cross_references']) and (unit['status']=='pending' or unit.get('reviewed')==DATE), 'Historical source revisited')
                original_unit=INDEX[unit['reference']]
                for k,v in original_unit.items():
                    if k not in {'book','file','ref'}: require(unit.get(k)==v, 'Native source field differs')
                target=[evidence(k) for k in keys(row['target'])]
                edge={'id':slug(unit['reference'])+'__'+slug(row['target']),'target':row['target'],'verdict':'supported','relationship':row['relationship'],'rationale':row['rationale'],'reviewed':DATE,'reviewer':a['reviewer'],'review_batch':RUN,'source_text_sha256':text_sha(unit['text']),'target_source':source(INDEX[target[0]['reference']]['book']),'target_verses':target,'target_passage_sha256':text_sha('\n'.join(t['reference']+' '+t['text'] for t in target)),'destination_anchor_check':'not performed; reference resolves to saved source records'}
                if unit.get('continuation_paragraphs'):edge['source_complete_text_sha256']=text_sha(complete_text(unit))
                if any(t.get('continuation_paragraphs') for t in target):edge['target_passage_complete_sha256']=text_sha('\n'.join(t['reference']+' '+complete_text(t) for t in target))
                unit['cross_references'].append(edge); unit.update(status='completed',reviewed=DATE)
            for kind,destination in [('deferred_source_units',deferred),('unresolved_candidates',candidates)]:
                for raw in p['cases'][kind]:
                    case=deepcopy(raw);case.update(source_snapshot=deepcopy(data['source_snapshot']),source_verse=evidence(case['source_reference']),reviewer=a['reviewer'],reviewed=DATE,review_timezone='America/New_York',review_batch=RUN,completed_source_credit=0,completed_pair_credit=0)
                    if kind=='unresolved_candidates':
                        kk=keys(case['target']);target=[evidence(k) for k in kk]
                        case.update(target_source=source(INDEX[kk[0]]['book']),target_verses=target,retained=False,identity_resolved=True,source_and_target_text_read=True,evidence_support_status='pending supported relationship; excluded from completion',target_passage_sha256=text_sha('\n'.join(t['reference']+' '+t['text'] for t in target)))
                        if any(t.get('continuation_paragraphs') for t in target):case['target_passage_complete_sha256']=text_sha('\n'.join(t['reference']+' '+complete_text(t) for t in target))
                    else:case.update(target=None,source_unit_read=True)
                    destination.append(case)
            for raw in p['cases']['unread_hints']:
                hint=deepcopy(raw);hint.update(source_and_target_text_read=False,completed_source_credit=0,completed_pair_credit=0,review_batch=RUN);all_hints.append(hint)
        checks.setdefault('deferred_source_units',[]).extend(deferred);checks.setdefault('unresolved_candidates',[]).extend(candidates)
        previously_read={v['reference'] for v in flat(before) if v['status']=='completed'}|{x['source_reference'] for x in oldchecks.get('deferred_source_units',[])}
        available=[v['reference'] for v in flat(before) if v['reference'] not in previously_read]
        require(cohort==available[:len(cohort)], 'Cohort is not the exact next native source-order prefix: '+book)
        for c in data['chapters']:c['status']='completed' if all(v['status']=='completed' for v in c['verses']) else 'pending'
        done=[v for v in flat(data) if v['status']=='completed'];pending=[v for v in flat(data) if v['status']!='completed'];edges=[e for v in done for e in v['cross_references']]
        drefs={d['source_reference'] for d in checks['deferred_source_units']}; unread=[v for v in pending if v['reference'] not in drefs]
        nextref=pending[0]['reference'] if pending else None; nextunread=unread[0]['reference'] if unread else None
        status='complete_initial_curated_pass' if not pending else ('initial_curated_pass_in_progress' if done else 'pending')
        data.update(date=DATE,completed_source_verses=len(done),completed_cross_references=len(edges),completed_chapters=completed_chapter_numbers(data),completed_source_sections=completed_source_sections(data),next_reference=nextref,next_unreviewed_reference=nextunread,review_status=status)
        read_count=len(previously_read)+len(cohort)
        checks.update(date=DATE,next_unreviewed_reference=nextunread,method='Complete actual source and target passages with necessary context were read and each retained explanation separately reread in recorded batches. Source-only deferrals and unresolved candidates receive zero completion credit. Technical inventory is separate from semantic review.',checked_scope={'source_passage':flat(data)[0]['reference']+' through '+(cohort[-1] if cohort else flat(data)[-1]['reference']) if read_count else None,'source_passage_is_review_scope':True,'source_units_read':read_count,'source_verse_units':len(done),'deferred_source_units':len(drefs),'retained_pairs':len(edges),'distinct_target_verse_units':len({t['reference'] for e in edges for t in e['target_verses']})})
        existing={s['path']:s for s in checks['sources']}
        if applicable:
            for name in sorted(pins):
                src=source(name)
                if src['path'] in existing: require(existing[src['path']]==src,'Historical source pin differs')
                else:checks['sources'].append(src)
            checks['review_batches'].append({'run_id':RUN,'records':'review-batches/'+RUN+'.json','new_source_verses':len({r['source_reference'] for r in rows}),'new_pairs':len(rows),'source_units_read':len(cohort),'first_reviewed_source_units':len(cohort),'revisited_source_units_read':0,'resolved_source_deferrals':0,'deferred_source_units':len(deferred),'unresolved_retained_cases':0})
        checks['pending']=['First pending source unit: '+str(nextref),f'{read_count} of {len(flat(data))} original source units read; {len(unread)} never reviewed. Deferred units remain incomplete.','Next never-reviewed source: '+str(nextunread)+'.','Read but deferred source units: '+', '.join(d['source_reference'] for d in checks['deferred_source_units']),'Independent specialist review','Live destination anchors and reader display checks']+['Unretained target candidate: '+c['source_reference']+' / '+c['target'] for c in checks['unresolved_candidates']]
        record=next(b for b in progress['books'] if b['book']==book)
        record.update(status='completed' if not pending else ('in_progress' if done else 'pending'),inventory_status='complete for pinned source',total_source_verse_units=data['total_source_verse_units'],total_chapters=data['total_chapters'],total_source_sections=data['total_source_sections'],completed_source_verses=len(done),completed_cross_references=len(edges),completed_chapters=data['completed_chapters'],completed_source_sections=data['completed_source_sections'],next_reference=nextref,next_unreviewed_reference=nextunread,completed_verse_ranges=[section_range(c) for c in data['chapters'] if c['status']=='completed'])
        if applicable:
            results.append({'book':book,'source_range':cohort[0]+' through '+cohort[-1],'source_range_is_review_scope':True,'source_references':cohort,'source_units_read':len(cohort),'first_reviewed_source_units':len(cohort),'revisited_source_units_read':0,'new_completed_revisited_sources':0,'distinct_source_verses':len({r['source_reference'] for r in rows}),'new_completed_pairs':len(rows),'new_deferred_source_units_count':len(deferred),'total_deferred_source_units_count':len(drefs),'completed_chapters':data['completed_chapters'],'new_completed_chapters':[c for c in data['completed_chapters'] if c not in before['completed_chapters']],'reviewed_dates':[DATE],'book_initial_curated_pass_complete':not pending,'all_original_source_units_read':not unread,'next_reference':nextref,'next_unreviewed_reference':nextunread})
        datasets[book]=data;checksets[book]=checks;all_deferred+=deferred;all_candidates+=candidates
        put(folder+'verses.json',encoded(data));put(folder+'source-checks.json',encoded(checks))
        restore=(REPO/folder/'RESTORE.md').read_text(encoding='utf-8')
        restore=restore.split('\n## Pending source review recovery\n')[0]
        local_pending=nextref or 'none; all original units read'; local_unread=nextunread or 'none; all original units read'
        restore+=f'\n\n## Pending source review recovery\n\n{data["total_source_verse_units"]} original source units in {data.get('chapter_display_label',str(data['total_chapters'])+' native chapters')} and {data["total_source_sections"]} native source groups remain unchanged. {read_count} read; {len(done)} supported sources; {len(edges)} pairs; {len(unread)} never reviewed. First pending within book: **{local_pending}**. Next never-reviewed within book: **{local_unread}**. Deferred sources have zero completion credit. Preserve all prior evidence and native ordering.\n'
        put(folder+'RESTORE.md',restore.encode())
    # Source review advances only when every prior book has no never-read units.
    reached_unread=False; nextnew=None
    for book in REVIEW_BOOKS:
        data=datasets[book]
        if reached_unread: require(not any(r['book']==book for r in results),'Source review skipped unread earlier book')
        if data['next_unreviewed_reference']:
            reached_unread=True
            if nextnew is None:
                ref=data['next_unreviewed_reference'];v=next(v for v in flat(data) if v['reference']==ref);nextnew={'book':book,'chapter':native_chapter_map(book)[ref],'reference':ref,'source_id':v['id']}
    if nextnew is None:
        order=[b['book'] for b in progress['books']];following=order[order.index(REVIEW_BOOKS[-1])+1];ref=next(ref for ref,u in INDEX.items() if u['book']==following);nextnew={'book':following,'chapter':1,'reference':ref,'source_id':INDEX[ref]['id']}
    progress.update(updated=DATE,updated_at_utc=datetime.now(timezone.utc).isoformat(),completed_source_verses=sum(b['completed_source_verses'] for b in progress['books']),completed_cross_references=sum(b['completed_cross_references'] for b in progress['books']),completed_chapters=sum(len(b.get('completed_chapters',[])) for b in progress['books']),completed_book_records=sum(b['status']=='completed' for b in progress['books']),next_unreviewed=nextnew)
    progress['pending_book_records']=len(progress['books'])-progress['completed_book_records']
    require(progress['next']==oldp['next'],'Earliest pending changed')
    nextrecord=next(b for b in progress['books'] if b['book']==nextnew['book'])
    inventory_note=' (inventory required before review)' if nextnew['book'] not in datasets and not (REPO/nextrecord['records']/'verses.json').exists() else ''
    for book in datasets:
        path=slug(book)+'/RESTORE.md'
        continuation=f'\nOverall continuation: earliest pending source overall is **{progress["next"]["reference"]}**. Next new source review: **{nextnew["reference"]}**{inventory_note}.\n'
        put(path,outputs[path]+continuation.encode())
    newpairs=sum(r['new_completed_pairs'] for r in results);newsources=sum(r['distinct_source_verses'] for r in results);readcount=sum(r['source_units_read'] for r in results);last=oldp['runs'][-1]
    run={'run_id':RUN,'date':DATE,'synchronized':DATE,'book_results':results,'source_units_read':readcount,'first_reviewed_source_units':readcount,'revisited_source_units_read':0,'new_completed_revisited_sources':0,'distinct_source_verses':newsources,'new_completed_pairs':newpairs,'new_deferred_source_units_count':len(all_deferred),'resolved_source_deferrals_count':0,'total_deferred_source_units_count':last['total_deferred_source_units_count']+len(all_deferred),'hourly_target':CONFIG.get('target_pairs',500),'target_met':newpairs>=CONFIG.get('target_pairs',500),'target_shortfall':max(0,CONFIG.get('target_pairs',500)-newpairs),'target_excess':max(0,newpairs-CONFIG.get('target_pairs',500)),'unresolved_retained_cases':0,'new_unresolved_candidate_count':len(all_candidates),'known_pending_target_candidate_count':last['known_pending_target_candidate_count']+len(all_candidates),'review_record':'review-batches/'+RUN+'.json','next_reference':progress['next']['reference'],'next_unreviewed_reference':nextnew['reference'],'inventories_added':[],'review_base_commit':BASE}
    progress['runs'].append(run);require(progress['runs'][:-1]==oldp['runs'] and len(progress['runs'])==len(oldp['runs'])+1,'Historical run mutation')
    archive_files=['run-config.json','incremental.py','passages.py','baseline-proof.json','source-review-gates.json','review-plan.json','production-render_books.py','source-registry.json']+registry['files']
    require((HERE/'technical-peer-review.json').exists(),'Independent technical acceptance is required')
    if (HERE/'technical-peer-review.json').exists():
        technical=load(HERE/'technical-peer-review.json')
        require(technical.get('disposition')=='accepted' and not technical.get('outstanding_findings'),'Technical peer acceptance missing')
        require((technical.get('run_id'),technical.get('base_commit',technical.get('baseline_commit')),technical.get('source_commit'))==(RUN,BASE,PIN),'Technical peer receipt identity differs')
        require(isinstance(technical.get('reviewer'),str) and technical['reviewer'].strip() and technical.get('completion_credit')==0,'Technical peer identity or zero-credit attestation missing')
        reviewed_files={item['file']:item['sha256'] for item in technical['files']}
        require(reviewed_files.get('incremental.py')==digest(HERE/'incremental.py'),'Technical peer must bind the final helper')
        archive_files.append('technical-peer-review.json')
        for kind in ['files','evidence']:
            for item in technical[kind]:
                name=item['file']
                require(isinstance(name,str) and name.strip() and not Path(name).is_absolute() and not Path(name).drive and '..' not in Path(name).parts,'Technical evidence must use a relative contained path')
                path=safe_path(HERE,name)
                require(path.is_file() and digest(path)==item['sha256'],'Changed technical peer input: '+name)
                if kind=='evidence':
                    require(path.suffix=='.json','Technical evidence must be an explicitly referenced JSON result')
                    archive_files.append(name)
    if (HERE/'publication-check.json').exists():archive_files.append('publication-check.json')
    frozen={name:value for p in plans.values() for name,value in p['frozen_inputs'].items()}
    archive_files+=list(frozen);archive_files=list(dict.fromkeys(archive_files))
    for name,value in frozen.items():require(digest(HERE/name)==value,'Changed final review packet')
    batch={**run,'source_repository':SOURCE_REPO,'source_commit':PIN,'reviewed':DATE,'completion_definition':progress['completion_definition'],'review_receipts':[p['author'] for p in plans.values()],'peer_review_receipts':[p['peer'] for p in plans.values()],'deferred_source_units':all_deferred,'unresolved_candidates':all_candidates,'unread_hints':all_hints,'unresolved_retained_cases':[],'unread_hints_completion_credit':0,'input_archive':ARCHIVE,'archived_input_files':[{'file':name,'sha256':digest(HERE/name),'completion_credit':0} for name in archive_files],'historical_evidence':{'baseline_commit':BASE,'prior_run_count':len(oldp['runs']),'preservation':'Existing historical objects and archives remain in Git history; no historical helper imported.'},'remaining_checks':['Independent specialist review','Live destination anchors and display verification']}
    put('progress.json',encoded(progress));put('review-batches/'+RUN+'.json',encoded(batch))
    for result in results:put(slug(result['book'])+'/review-batches/'+RUN+'.json',encoded({**batch,**result,'overall_review_record':'../../review-batches/'+RUN+'.json'}))
    for item in batch['archived_input_files']:put(ARCHIVE+item['file'],(HERE/item['file']).read_bytes())
    put(ARCHIVE+'.gitattributes',b'* -text whitespace=cr-at-eol\n')
    # Render all books in scratch with the unchanged production renderer.
    stage=HERE/('prepared-'+uuid.uuid4().hex);stage.mkdir()
    for path,raw in outputs.items():
        dest=safe_path(stage,path);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    (stage/'README.md').write_bytes((REPO/'README.md').read_bytes())
    for record in progress['books']:
        folder=record['records'];book=record['book'];current=REPO/folder
        if book not in datasets and not (current/'verses.json').exists():continue
        dest=stage/folder;dest.mkdir(parents=True,exist_ok=True)
        for name in ['verses.json','source-checks.json','README.md']:
            if not (dest/name).exists():
                src=current/name
                (dest/name).write_bytes(src.read_bytes())
        if book=='Genesis':(dest/'Genesis.html').write_bytes((current/'Genesis.html').read_bytes())
    render=module('current_renderer',REPO/'scripts/render_books.py');render.ROOT=stage
    with contextlib.redirect_stdout(io.StringIO()):render.main()
    put('README.md',(stage/'README.md').read_bytes())
    for record in progress['books']:
        folder=record['records'];file=stage/folder/'verses.json'
        if not file.exists():continue
        data=load(file)
        for name in ['README.md',data['readable_html'],data['readable_text']]:
            raw=(stage/folder/name).read_bytes();existing=REPO/folder/name
            if not existing.exists() or raw.replace(b'\r\n',b'\n')!=existing.read_bytes().replace(b'\r\n',b'\n'):put(folder+name,raw)
    oldnext=oldp['next_unreviewed']['reference']
    for record in progress['books']:
        if record['book'] in datasets:continue
        for name in ['source-checks.json','RESTORE.md']:
            path=record['records']+name;file=REPO/path
            if not file.exists():continue
            raw=file.read_bytes();value=raw.decode('utf-8')
            for prefix,suffix in [('Next new source review: ','.'),('Next new source review: **','**'),('Next never-reviewed source: ','.'),('The next new source review is **','**'),('separate next_unreviewed at **','**')]:value=value.replace(prefix+oldnext+suffix,prefix+nextnew['reference']+suffix)
            if not inventory_note:value=value.replace(nextnew['reference']+'** (inventory required before review)',nextnew['reference']+'**')
            if name=='source-checks.json':
                before_checks=json.loads(raw);after_checks=json.loads(value)
                require({k:v for k,v in before_checks.items() if k!='pending'}=={k:v for k,v in after_checks.items() if k!='pending'},'Historical source checks changed outside continuation guidance')
            if value.encode()!=raw:put(path,value.encode())
    outputs={path:raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n',b'\n') for path,raw in outputs.items()}
    audit_objects(datasets,progress,checksets,outputs)
    for path,raw in outputs.items():
        dest=safe_path(stage,path);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
        current=(REPO/path).read_bytes() if (REPO/path).exists() else None
        require(current==original_outputs[path],'Output changed during preparation: '+path)
    summary={'run_id':RUN,'source_units_read':readcount,'new_completed_sources':newsources,'new_pairs':newpairs,'new_deferred_sources':len(all_deferred),'new_candidates':len(all_candidates),'completed_source_verses':progress['completed_source_verses'],'completed_pairs':progress['completed_cross_references'],'completed_chapters':progress['completed_chapters'],'next':progress['next'],'next_unreviewed':nextnew,'book_results':results,'output_files':len(outputs),'archive_files':len(archive_files),'review_base_commit':BASE,'observed_head':head,'staging_directory':str(stage)}
    manifest={'run_id':RUN,'stage':str(stage),'summary':summary,'publication_parent_commit':head,'preserved_canon_git_blob_sha':blob(original('canon.json',head)),'frozen_inputs':batch['archived_input_files'],'outputs':[{'path':path,'sha256':sha(raw),'before_sha256':sha(original_outputs[path]) if original_outputs[path] is not None else None} for path,raw in outputs.items()]}
    (HERE/'prepared-manifest.json').write_bytes(encoded(manifest));return outputs,manifest

def audit_objects(datasets,progress,checksets,outputs=None):
    oldp=load(HERE/'before-progress.json');require(progress['runs'][:-1]==oldp['runs'],'Prior runs changed');total=0
    for a,b in zip(oldp['books'],progress['books']):
        if a['book'] not in datasets:require(a==b,'Unrelated book record changed')
    for book,data in datasets.items():
        before=existing_book(book);checks=checksets[book];oldchecks=existing_checks(book)
        cohort={r for stem in STEMS if STEMS[stem]==book for r in ordered_scope(stem)}
        old_read=previously_read_refs(book)
        mutable={'date','completed_source_verses','completed_cross_references','completed_chapters','completed_source_sections','next_reference','next_unreviewed_reference','review_status'}
        require({k:v for k,v in before.items() if k not in mutable and k!='chapters'}=={k:v for k,v in data.items() if k not in mutable and k!='chapters'},'Historical top-level book metadata changed')
        for field in ['deferred_source_units','unresolved_candidates','review_batches','sources']:
            require(checks.get(field,[])[:len(oldchecks.get(field,[]))]==oldchecks.get(field,[]),'Historical source-check entries changed: '+field)
        mutable_checks={'date','next_unreviewed_reference','method','checked_scope','sources','review_batches','deferred_source_units','unresolved_candidates','pending'}
        require({k:v for k,v in oldchecks.items() if k not in mutable_checks}=={k:v for k,v in checks.items() if k not in mutable_checks},'Historical source-check metadata changed')
        require(len(checks['review_batches'])==len(oldchecks['review_batches'])+1,'Existing review-batch history was not appended exactly once')
        require(data['source_metadata']==before['source_metadata'] and data['source_snapshot']==before['source_snapshot'],'Source metadata or pin changed')
        require(len(flat(data))==len(flat(before)) and len(data['chapters'])==len(before['chapters']),'Inventory shape changed')
        for old,new in zip(before['chapters'],data['chapters']):require({k:v for k,v in old.items() if k not in {'verses','status'}}=={k:v for k,v in new.items() if k not in {'verses','status'}},'Section metadata changed')
        for old,new in zip(flat(before),flat(data)):
            if old['reference'] not in cohort:require(old==new,'Source object outside current cohort changed')
            if old['status']=='completed':require(old==new,'Historical completed object changed')
            if old['reference'] in cohort:require(old['status']=='pending' and not old['cross_references'] and old['reference'] not in old_read,'Historical source was revisited')
            require({k:v for k,v in old.items() if k not in {'cross_references','status','reviewed'}}=={k:v for k,v in new.items() if k not in {'cross_references','status','reviewed'}},'Native unit changed')
            for edge in new['cross_references']:
                if edge.get('review_batch')!=RUN:continue
                target=[evidence(k) for k in keys(edge['target'])]
                require(edge['target_verses']==target,'Complete target/native evidence differs')
                require(edge['source_text_sha256']==text_sha(new['text']) and edge['target_passage_sha256']==text_sha('\n'.join(t['reference']+' '+t['text'] for t in target)),'Evidence hash mismatch');total+=1
        done=[v for v in flat(data) if v['status']=='completed'];edges=[e for v in done for e in v['cross_references']]
        require((len(done),len(edges))==(data['completed_source_verses'],data['completed_cross_references']),'Book totals mismatch')
        require(len({e['id'] for e in edges})==len(edges),'Duplicate edge IDs')
        require(data['completed_chapters']==completed_chapter_numbers(data) and data['completed_source_sections']==completed_source_sections(data),'Native chapter aggregation mismatch')
        if outputs:
            validator=module('current_validator',REPO/'scripts/validate.py');parser=validator.Anchors();folder=slug(book)+'/'
            parser.feed(outputs[folder+data['readable_html']].decode())
            require(parser.scripture==[complete_text(v) for v in done] and parser.target_scripture==[t['reference']+' '+complete_text(t) for e in edges for t in e['target_verses']],'Rendered complete Scripture differs')
            require(Counter(parser.ids)==Counter(v['id'] for v in done) and parser.details==len(edges),'Rendered anchors/pairs differ')
            txt=outputs[folder+data['readable_text']].decode()
            for v in done:require(v['reference']+'\n'+complete_text(v)+'\n' in txt,'Readable complete source missing')
    require(total==progress['runs'][-1]['new_completed_pairs'],'Current pair total mismatch')
    require(progress['completed_source_verses']==sum(b['completed_source_verses'] for b in progress['books']) and progress['completed_cross_references']==sum(b['completed_cross_references'] for b in progress['books']),'Root totals mismatch')
    return {'result':'passed','new_pairs_checked':total,'historical_runs_preserved':len(oldp['runs']),'historical_completed_objects_preserved':True,'new_inventories':[],'completion_credit':0}


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
        # Replacement can succeed before an interrupt prevents bookkeeping.
        # Inspect every durable prepared entry, including those still marked prepared.
        for item in reversed(journal['entries']):
            restore_temp = None
            try:
                path = safe_path(REPO, item['path'])
                current_hash = digest(path) if path.exists() else None
                if current_hash == item['before_sha256']:
                    item['state'] = 'rolled_back'; continue
                require(current_hash == item['sha256'], 'Concurrent bytes before rollback')
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
                # A restore may itself succeed immediately before an interrupt.
                # Report the verified final bytes instead of a false conflict.
                try:
                    path = safe_path(REPO, item['path'])
                    restored = (digest(path) if path.exists() else None) == item['before_sha256']
                except BaseException:
                    restored = False
                if restored:
                    item['state'] = 'rolled_back'; item['rollback_completed_after_exception'] = repr(rollback_error)
                else:
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
    """Capture fresh production validation receipts and derived continuation outputs."""
    progress=load(REPO/'progress.json');allowed={'README.md'};changed=set(git('diff','--name-only',BASE).decode().splitlines())
    parser_module=module('maintenance_parser',REPO/'scripts/validate.py');run_start=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    oldnext=load(HERE/'before-progress.json')['next_unreviewed']['reference'];newnext=progress['next_unreviewed']['reference'];verified=[]
    existing={item['path']:item for item in manifest['outputs']}
    for record in progress['books']:
        folder=record['records'];path=REPO/folder/'verses.json'
        if not path.exists():continue
        data=load(path);vp=folder+'verification.json';actual=load(REPO/vp)
        require(datetime.fromisoformat(actual['checked_at_utc'])>=run_start,'Run full production validate --write-verification: '+record['book'])
        actual_without_time={k:v for k,v in actual.items() if k!='checked_at_utc'}
        expected=json.loads(original(vp))
        expected.pop('checked_at_utc');expected.update(completed_source_verses=data['completed_source_verses'],completed_chapters=data['completed_chapters'],completed_cross_references=data['completed_cross_references'],unique_pair_ids=data['completed_cross_references'])
        require(actual_without_time==expected,'Production verification schema/count differs: '+record['book'])
        allowed.update(folder+name for name in ['README.md',data['readable_html'],data['readable_text'],'verification.json']);verified.append(record['book'])
        if record['book'] in REVIEW_BOOKS:continue
        hp=folder+data['readable_html'];tp=folder+data['readable_text']
        if hp in changed:
            old=parser_module.Anchors();new=parser_module.Anchors();old.feed(original(hp).decode().replace('\r\n','\n'));new.feed((REPO/hp).read_text(encoding='utf-8'))
            for field in ['ids','details','scripture','target_scripture']:require(getattr(old,field)==getattr(new,field),'Historical rendered Scripture changed: '+hp)
        if tp in changed:
            old=original(tp).decode().replace('\r\n','\n')
            for prefix in ['Next new source review: ','Next never-reviewed source: ']:old=old.replace(prefix+oldnext+'.',prefix+newnext+'.')
            waiting=len(json.loads(original(folder+'source-checks.json')).get('unresolved_candidates',[]))
            old=old.replace('\n'+f'{waiting} target candidate(s) await source evidence or identity review and are excluded from completed pair totals; see source-checks.json.'+'\n','\n'+f'{waiting} target candidate(s) remain unretained and are excluded from completed pair totals; see the recorded reasons in source-checks.json.'+'\n',1)
            require((REPO/tp).read_text(encoding='utf-8')==old,'Historical plain text differs beyond continuation: '+tp)
    require(set(verified)=={b['book'] for b in baseline_records()},'Expected every existing technical receipt')
    for path,item in existing.items():
        if path in allowed or path=='progress.json':continue
        raw=(REPO/path).read_bytes();raw=raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n',b'\n')
        require(sha(raw)==item['sha256'],'Protected output changed before maintenance capture: '+path)
    captured=sorted((changed|set(existing)|{b['records']+'verification.json' for b in progress['books'] if (REPO/b['records']/'verses.json').exists()})&allowed)
    for path in captured:
        raw=(REPO/path).read_bytes().replace(b'\r\n',b'\n');item=existing.get(path,{'path':path,'maintenance_only':True});item['sha256']=sha(raw);existing[path]=item
        dest=safe_path(Path(manifest['stage']),path);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    manifest['outputs']=list(existing.values());manifest['maintenance']={'required_external_commands':['python scripts/render_genesis.py','python scripts/validate.py --write-verification'],'renderer_compatibility_entrypoint':'render_genesis.py calls render_books.main','fresh_production_verification_books':verified,'historical_scripture_bodies_preserved':True,'captured_derived_files':captured,'completion_credit':0}
    (HERE/'prepared-manifest.json').write_bytes(encoded(manifest));return manifest

def readback(ref=None):
    manifest=load(HERE/'prepared-manifest.json')
    if not ref:manifest=capture_maintenance(manifest)
    def get(path):
        raw=original(path,ref) if ref else (REPO/path).read_bytes()
        return raw if path.startswith(ARCHIVE) else raw.replace(b'\r\n',b'\n')
    progress=json.loads(get('progress.json'));expected=load(Path(manifest['stage'])/'progress.json')
    require(without_nt(progress)==without_nt(expected),'Readback OT progress differs')
    for item in manifest['outputs']:
        if item['path']=='progress.json':continue
        require(sha(get(item['path']))==item['sha256'],'Readback output differs: '+item['path'])
    for record in baseline_records():
        for name in ['verses.json','inventory.json','editorial-notes.json']:
            path=record['records']+name
            if path not in baseline_files():continue
            if record['book'] in REVIEW_BOOKS and name=='verses.json':continue
            require(get(path)==original(path).replace(b'\r\n',b'\n'),'Historical book record changed: '+path)
            if ref:require(blob(original(path,ref))==blob(original(path)),'Historical Git blob changed: '+path)
    for path in ['scripts/render_genesis.py','scripts/render_books.py','scripts/chapter_structure.py','scripts/validate.py']:
        require(get(path)==original(path).replace(b'\r\n',b'\n'),'Production maintenance code changed: '+path)
    require(blob(original('canon.json',ref or 'HEAD'))==manifest['preserved_canon_git_blob_sha'],'Fresh publication-parent canon Git blob changed')
    require(newline_only_root_change('canon.json',ref),'Canon content changed beyond permitted newline normalization')
    allowed={i['path'] for i in manifest['outputs']};changed=git('diff','--name-only',BASE,ref if ref else 'HEAD').decode().splitlines()
    if not ref:changed+=git('diff','--name-only','HEAD').decode().splitlines()
    require(all(p in allowed or is_nt(p) or (p=='canon.json' and newline_only_root_change(p,ref)) for p in changed),'Unrelated historical file changed: '+', '.join(p for p in changed if p not in allowed and not is_nt(p) and not (p=='canon.json' and newline_only_root_change(p,ref))))
    datasets={b:json.loads(get(slug(b)+'/verses.json')) for b in REVIEW_BOOKS};checks={b:json.loads(get(slug(b)+'/source-checks.json')) for b in datasets}
    rendered={slug(b)+'/'+d[k]:get(slug(b)+'/'+d[k]) for b,d in datasets.items() for k in ['readable_html','readable_text']}
    result=audit_objects(datasets,progress,checks,rendered);result.update(ref=ref or 'working tree',historical_book_records_preserved=len(baseline_records()),technical_receipts=len(manifest.get('maintenance',{}).get('fresh_production_verification_books',[])),scope='Only current run inputs/outputs and changed paths checked; historical evidence preserved by Git identity without rereview credit.')
    (HERE/('published-readback.json' if ref else 'preservation-audit.json')).write_bytes(encoded(result));return result


def publication_check(ref):
    """Read-only check for a normal concurrent NT merge; never resets or reapplies review."""
    changed = git('diff', '--name-only', BASE, ref).decode().splitlines()
    require(all(is_nt(p) or p == 'progress.json' or newline_only_root_change(p,ref) for p in changed), 'Remote contains concurrent OT changes')
    remote = json.loads(original('progress.json', ref)); before = load(HERE / 'before-progress.json')
    require(without_nt(remote) == without_nt(before), 'Remote OT objects differ from review baseline')
    result = {'remote_ref': ref, 'remote_commit': git('rev-parse', ref).decode().strip(), 'review_base_commit': BASE, 'only_independent_nt_changes': True, 'remote_nt_pointer': remote.get('new_testament_tracker'), 'merge_instruction': 'Perform a normal Git merge. If only progress.json conflicts, preserve the complete local OT object and replace only new_testament_tracker with remote_nt_pointer. Do not reset or regenerate the semantic batch.', 'completion_credit': 0}
    result['newline_only_root_files']=[{'path':p,'baseline_blob_sha':blob(original(p)),'remote_blob_sha':blob(original(p,ref)),'normalized_bytes_equal':True} for p in changed if p in {'canon.json','README.md'}]
    result['fresh_remote_canon_blob_sha']=blob(original('canon.json',ref))
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
    # Keep terminal summaries compact; the full explicit cohorts remain in the manifest.
    printable=deepcopy(result)
    if isinstance(printable,dict) and 'book_results' in printable:
        printable['book_results']=[{k:v for k,v in b.items() if k!='source_references'} for b in printable['book_results']]
    print(json.dumps(printable, ensure_ascii=False))

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); main()
