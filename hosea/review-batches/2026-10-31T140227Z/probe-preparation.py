"""Current new-book fixture. Synthetic pairs give zero real completion credit."""
from pathlib import Path
import contextlib,io,json,shutil,subprocess,sys,uuid
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import incremental as m
partial='--partial' in sys.argv
full_native_count=sum(len(p['source_references']) for p in m.PLAN['packets']);expected_books=len(m.baseline_records())+len(m.NEW_BOOKS)
book_order=[b['book'] for b in m.load(H/'before-progress.json')['books']];future_book=book_order[book_order.index(m.REVIEW_BOOKS[-1])+1];future_ref=next(r for r,u in m.INDEX.items() if u['book']==future_book)
S=H/('p-'+uuid.uuid4().hex[:8]);S.mkdir()
names=['run-config.json','review-plan.json','incremental.py','passages.py','baseline-proof.json','production-render_books.py','production-validate.py','inventory-books.py']+[p.name for p in H.glob('before-*.json')]
for book in m.NEW_BOOKS:
    stem=m.slug(book);names+=['inventory-'+stem+'-receipt.json',stem+'-seed.json',stem+'-inventory.json']
    shutil.copytree(H/('new-'+stem),S/('new-'+stem))
for name in list(dict.fromkeys([n for n in names if n.startswith('before-')]+list(m.declared_evidence_closure([n for n in names if not n.startswith('before-')])))):
    dest=S/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(H/name,dest)
if partial:
    m.PLAN=json.loads(json.dumps(m.PLAN));last_native=m.PLAN['packets'][-1]['source_references'].pop()
    m.PLAN['packets'][-1]['source_units']=len(m.PLAN['packets'][-1]['source_references'])
    (S/'review-plan.json').write_bytes(m.encoded(m.PLAN))
pins=[{'book':b,'path':m.slug(b)+'/verses.json','blob_sha':m.book_data(b)['source_snapshot']['blob_sha']} for b in m.REVIEW_BOOKS]
registry={'books':pins,'files':[],'synthetic_fixture':True,'completion_credit':0}
(S/'source-registry.json').write_bytes(m.encoded(registry))
leaf={'synthetic_fixture':True,'completion_credit':0};(S/'nested-fixture-leaf.json').write_bytes(m.encoded(leaf))
top={'full_triples_file':'nested-fixture-leaf.json','full_triples_sha256':m.digest(S/'nested-fixture-leaf.json')};(S/'nested-fixture-top.json').write_bytes(m.encoded(top))
plans={};gates=[]
for stem,book in m.STEMS.items():
    refs=m.ordered_scope(stem);rows=[{'source_reference':r,'target':'Joel 1:1' if r.startswith('Hosea ') else 'Hosea 1:1','relationship':'Synthetic fixture','rationale':'Technical check only; zero semantic credit.'} for r in refs]
    cases={'deferred_source_units':[],'unresolved_candidates':[],'unread_hints':[]}
    if partial and book!='Hosea':
        rows=rows[:1];cases['deferred_source_units']=[{'source_reference':r,'reason':'Synthetic technical fixture only.','target':None,'completed_pair_credit':0} for r in refs[1:]]
    plans[stem]={'rows':rows,'cohort':refs,'cases':cases,'author':{'reviewer':'SCRATCH FIXTURE'},'peer':None,'frozen_inputs':{'nested-fixture-top.json':m.digest(S/'nested-fixture-top.json')}}
    gates.append({'packet_stem':stem,'source_book':book,'source_units_read_this_run':len(refs),'all_actual_cohort_units_read_in_native_order':True,'synthetic_fixture':True})
(S/'source-review-gates.json').write_bytes(m.encoded({'run_id':m.RUN,'baseline_commit':m.BASE,'source_commit':m.PIN,'gates':gates,'completion_credit':0}))
(S/'technical-peer-review.json').write_bytes(m.encoded({'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'reviewer':'SCRATCH FIXTURE','disposition':'accepted','outstanding_findings':[],'files':[{'file':n,'sha256':m.digest(S/n)} for n in ['incremental.py','production-render_books.py','production-validate.py','inventory-books.py']],'evidence':[],'completion_credit':0}))
m.HERE=S;m.packets=lambda require_peers=True:plans;m.verified_registry=lambda:registry
outputs,manifest=m.prepare();stage=Path(manifest['stage']);expected=sum(len(p['rows']) for p in plans.values())
(stage/'canon.json').write_bytes((m.REPO/'canon.json').read_bytes())
for b in m.baseline_records():
    for n in ['inventory.json','editorial-notes.json']:
        p=m.REPO/b['records']/n
        if p.exists():shutil.copyfile(p,stage/b['records']/n)
validator=m.module('fixture_validator',S/'production-validate.py');validator.ROOT=stage
def repository_path(relative):
    p=m.safe_path(stage,relative)
    return p if p.exists() or relative.replace('\\','/') not in m.baseline_files() else m.safe_path(m.REPO,relative)
validator.repository_path=repository_path
with contextlib.redirect_stdout(io.StringIO()):validator.validate(True)
old=m.load(H/'before-progress.json');new=m.load(stage/'progress.json');checks={}
def ck(label,value):checks[label]=bool(value);m.require(value,label)
ck('all50oldruns',new['runs'][:-1]==old['runs'] and len(old['runs'])==50)
ck('current_native_source_count',manifest['summary']['source_units_read']==full_native_count-int(partial))
ck('synthetic_pair_count',manifest['summary']['new_pairs']==expected)
ck('earliest_pending',new['next']==old['next'])
ck('continuation',new['next_unreviewed']['reference']==(last_native if partial else future_ref))
ck('future_book_unchanged',next(x for x in new['books'] if x['book']==future_book)==next(x for x in old['books'] if x['book']==future_book))
ck('no_future_book_seed',not (stage/m.slug(future_book)).exists())
ck('no_production_code_outputs',not any(p.startswith('scripts/') for p in outputs))
ck('fresh_actual_validation_all_books',sum((stage/b['records']/'verification.json').exists() for b in new['books'])==expected_books)
ck('NT_pointer',new['new_testament_tracker']==old['new_testament_tracker'])
for b in m.baseline_records():
    f=b['records'];data=m.load(stage/f/'verses.json');before=m.load(H/('before-'+(f+'verses.json').replace('/','__')))
    ck(f+'all_old_completion_objects',data==before)
    parser=validator.Anchors();parser.feed((stage/f/data['readable_html']).read_text(encoding='utf-8'))
    oldparser=validator.Anchors();oldparser.feed((m.REPO/f/data['readable_html']).read_text(encoding='utf-8'))
    ck(f+'old_Scripture_anchors',parser.scripture==oldparser.scripture and parser.ids==oldparser.ids)
for b in m.REVIEW_BOOKS:
    stem=m.slug(b);data=m.load(stage/stem/'verses.json');seed=m.load(H/(stem+'-seed.json'))
    strip=lambda d:[{k:v for k,v in u.items() if k not in {'status','cross_references','reviewed'}} for u in m.flat(d)]
    ck(stem+'original_fields_and_order',strip(data)==strip(seed))
    ck(stem+'inventory_exact',(stage/stem/'inventory.json').read_bytes()==(H/('new-'+stem)/'inventory.json').read_bytes())
    ck(stem+'recovery_pointers','1 Chronicles 1:24' in outputs[stem+'/RESTORE.md'].decode() and new['next_unreviewed']['reference'] in outputs[stem+'/RESTORE.md'].decode())
ck('explicit_nested_evidence_archived',outputs[m.ARCHIVE+'nested-fixture-leaf.json']==(S/'nested-fixture-leaf.json').read_bytes())
ck('nested_evidence_hash_bound',any(x['file']=='nested-fixture-leaf.json' and x['sha256']==m.digest(S/'nested-fixture-leaf.json') for x in manifest['frozen_inputs']))
real_repo=m.REPO;(stage/'scripts').mkdir(exist_ok=True)
for name in ['chapter_structure.py','render_genesis.py','render_books.py','validate.py']:shutil.copyfile(real_repo/'scripts'/name,stage/'scripts'/name)
def fixture_git(*args):
    if args==('diff','--name-only',m.BASE):return ('\n'.join(sorted(outputs))+'\n').encode()
    return subprocess.check_output(['git',*args],cwd=real_repo)
m.REPO=stage;m.git=fixture_git
with contextlib.redirect_stdout(io.StringIO()):audit=m.readback()
ck('actual_maintenance_readback',audit['technical_receipts']==expected_books)
ck('unchanged_production_code',all((stage/p).read_bytes()==raw for p,raw in m.reviewed_code().items()))
ck('real_tracker_clean',subprocess.check_output(['git','status','--porcelain'],cwd=real_repo)==b'')
result={'run_id':m.RUN,'helper_sha256':m.digest(H/'incremental.py'),'driver_sha256':m.digest(H/'probe-preparation.py'),'synthetic_fixture':True,'partial':partial,'synthetic_pairs':expected,'completion_credit':0,'repo_mutations':0,'checks':checks}
(S/'result.json').write_bytes(m.encoded(result));print(json.dumps({'result':str(S/'result.json'),'checks_passed':len(checks),'synthetic_pairs':expected,'zero_credit':True}))
