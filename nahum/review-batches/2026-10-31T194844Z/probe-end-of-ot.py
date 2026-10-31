"""Scratch-only end-of-OT technical fixture. Never semantic review or production output."""
from pathlib import Path
from copy import deepcopy
import hashlib, importlib.util, json, shutil, sys, contextlib, io
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;R=H.parent/'saints-crossrefs';F=H/'end-of-ot-probe'
sys.path.insert(0,str(H));sys.path.insert(0,str(R/'scripts'))
import incremental as inc
load=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def reject(action):
    try:action()
    except ValueError:return True
    raise AssertionError('Invalid continuation was accepted')
F.mkdir(exist_ok=True)
binding=F/'code-binding-fixture';binding.mkdir(exist_ok=True)
for name in ['incremental.py','production-render_books.py','production-validate.py']:shutil.copyfile(H/name,binding/name)
receipt={'run_id':inc.RUN,'base_commit':inc.BASE,'source_commit':inc.PIN,'reviewer':'TECHNICAL FIXTURE ONLY; no actual peer acceptance','disposition':'accepted','outstanding_findings':[],'completion_credit':0,'files':[{'file':name,'sha256':sha(binding/name)} for name in ['incremental.py','production-render_books.py','production-validate.py']]}
prior_here=inc.HERE
try:
    inc.HERE=binding
    # A null disposition stands for absent acceptance without deleting fixture files.
    invalid=deepcopy(receipt);invalid['disposition']=None;save(binding/'technical-peer-review.json',invalid)
    assert reject(inc.reviewed_code)
    invalid=deepcopy(receipt);invalid['run_id']='wrong-run';save(binding/'technical-peer-review.json',invalid)
    assert reject(inc.reviewed_code)
    for stale_name in ['incremental.py','production-render_books.py','production-validate.py']:
        invalid=deepcopy(receipt);next(x for x in invalid['files'] if x['file']==stale_name)['sha256']='0'*64;save(binding/'technical-peer-review.json',invalid)
        assert reject(inc.reviewed_code)
    save(binding/'technical-peer-review.json',receipt)
    captured_code=inc.reviewed_code()
    assert captured_code=={path:(H/name).read_bytes() for path,name in [('scripts/render_books.py','production-render_books.py'),('scripts/validate.py','production-validate.py')]}
finally:inc.HERE=prior_here
progress=load(H/'before-progress.json');before=deepcopy(progress)
assert inc.following_source_review(progress,'Malachi') is None
assert inc.following_source_review(progress,'Nahum')['book']=='Habakkuk'
for record in progress['books']:
    slug=record['records'].rstrip('/');src=R/slug if (R/slug/'verses.json').exists() else H/('new-'+slug);dest=F/slug;dest.mkdir(exist_ok=True)
    for name in ['verses.json','source-checks.json','README.md','inventory.json']:
        if (src/name).exists():shutil.copyfile(src/name,dest/name)
    if not (R/slug/'verses.json').exists():
        data=load(dest/'verses.json');checks=load(dest/'source-checks.json');units=[u for c in data['chapters'] for u in c['verses']]
        # Deliberately simulate all remaining sources read-but-deferred. This fixture
        # carries no semantic attestation and must never be published as review.
        checks['deferred_source_units']=[{'source_reference':u['reference'],'reason':'TECHNICAL FIXTURE ONLY; no source or target review claimed.','completed_source_credit':0,'completed_pair_credit':0} for u in units]
        data['next_unreviewed_reference']=None;checks['next_unreviewed_reference']=None
        record.update(inventory_status='complete for pinned source',total_source_verse_units=data['total_source_verse_units'],total_chapters=data['total_chapters'],total_source_sections=data['total_source_sections'],completed_chapters=[],completed_source_sections=[],next_reference=units[0]['reference'],next_unreviewed_reference=None)
        save(dest/'verses.json',data);save(dest/'source-checks.json',checks)
progress['next_unreviewed']=None
assert progress['next']==before['next'] and progress['completed_source_verses']==before['completed_source_verses'] and progress['completed_cross_references']==before['completed_cross_references']
save(F/'progress.json',progress);shutil.copyfile(H/'before-canon.json',F/'canon.json');shutil.copyfile(R/'README.md',F/'README.md');shutil.copyfile(R/'genesis/Genesis.html',F/'genesis/Genesis.html')
validator=module('end_probe_validator',H/'production-validate.py');validator.ROOT=F
assert validator.validate_source_review_continuation(progress) is None
bad=deepcopy(progress);bad['next_unreviewed']={'book':'Matthew','chapter':1,'reference':'Matthew 1:1','source_id':'v1-1'}
assert reject(lambda:validator.validate_source_review_continuation(bad))
malachi=F/'malachi';checks=load(malachi/'source-checks.json');saved=deepcopy(checks);first=checks['deferred_source_units'].pop(0)['source_reference'];save(malachi/'source-checks.json',checks)
data=load(malachi/'verses.json');data['next_unreviewed_reference']=first;save(malachi/'verses.json',data)
record=progress['books'][-1];record['next_unreviewed_reference']=first
assert reject(lambda:validator.validate_source_review_continuation(progress))
progress['next_unreviewed']={'book':'Malachi','chapter':1,'reference':first,'source_id':data['chapters'][0]['verses'][0]['id']}
assert validator.validate_source_review_continuation(progress)==progress['next_unreviewed']
data['next_unreviewed_reference']=None;record['next_unreviewed_reference']=None;progress['next_unreviewed']=None
save(malachi/'source-checks.json',saved);save(malachi/'verses.json',data);save(F/'progress.json',progress)
protected={str(p.relative_to(F)):sha(p) for folder in progress['books'] for p in [F/folder['records']/'verses.json',F/folder['records']/'source-checks.json']}
renderer=module('end_probe_renderer',H/'production-render_books.py');renderer.ROOT=F
with contextlib.redirect_stdout(io.StringIO()):renderer.main()
assert all(sha(F/n)==s for n,s in protected.items())
label='Next new source review: none; all OT source units read.'
assert label in (F/'README.md').read_text(encoding='utf-8')
assert 'Next: 1 Chronicles 1:24.' in (F/'README.md').read_text(encoding='utf-8')
for stem in ['micah','1-chronicles','malachi']:
    d=load(F/stem/'verses.json')
    for name in ['README.md',d['readable_html'],d['readable_text']]:assert label in (F/stem/name).read_text(encoding='utf-8'),(stem,name)
for stem in ['micah','1-chronicles']:
    d=load(F/stem/'verses.json');old=validator.Anchors();new=validator.Anchors();old.feed((R/stem/d['readable_html']).read_text(encoding='utf-8'));new.feed((F/stem/d['readable_html']).read_text(encoding='utf-8'))
    for field in ['ids','details','scripture','target_scripture']:assert getattr(old,field)==getattr(new,field),(stem,field)
    expected=(R/stem/d['readable_text']).read_text(encoding='utf-8')
    for prefix in ['Next new source review: ','Next never-reviewed source: ']:expected=expected.replace(prefix+'Nahum 1:1.',prefix+inc.END_OF_OT+'.')
    assert (F/stem/d['readable_text']).read_text(encoding='utf-8')==expected
result={'run_id':inc.RUN,'scope':'Scratch-only technical simulation; no semantic source review or production mutation.','result':'passed','end_of_ot_pointer':None,'new_testament_source_rejected':True,'unread_malachi_with_null_pointer_rejected':True,'exact_unread_malachi_pointer_accepted':True,'earliest_pending_preserved':progress['next'],'all_incomplete_statuses_preserved':True,'new_completed_source_credit':0,'new_pair_credit':0,'completion_credit':0,'all_fixture_scripture_and_source_check_bytes_preserved_by_renderer':True,'historical_source_target_bodies_and_anchors_preserved':True,'readable_explicit_end_label':label,'helper_reference':{'file':'incremental.py','sha256':sha(H/'incremental.py')},'renderer_reference':{'file':'production-render_books.py','sha256':sha(H/'production-render_books.py')},'validator_reference':{'file':'production-validate.py','sha256':sha(H/'production-validate.py')}}
result.update(unaccepted_technical_receipt_rejected=True,wrong_run_technical_receipt_rejected=True,stale_helper_renderer_validator_digests_rejected=True,exact_technically_bound_proposed_code_bytes_captured=True,fixture_receipt_scope='Synthetic probe only in end-of-ot-probe/code-binding-fixture; not an actual technical acceptance receipt and not publication evidence.')
save(H/'end-of-ot-probe-result.json',result);print(json.dumps(result,indent=2))
