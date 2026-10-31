from pathlib import Path
import ast,hashlib,json,datetime
H=Path(__file__).resolve().parent
def load(n): return json.loads((H/n).read_text(encoding='utf-8-sig'))
def sha(n): return hashlib.sha256((H/n).read_bytes()).hexdigest()
def entry(n): return {'file':n,'sha256':sha(n)}
c=load('run-config.json');checks={}
def ck(n,v):
    assert v,n
    checks[n]=True
def funcs(p):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
old=funcs(H.parent/'hourly-2026-10-31-0808/incremental.py');new=funcs(H/'incremental.py')
ck('helper_delta_scope',{n for n in old if old[n]!=new.get(n)}=={'reviewed_code','prepare','audit_objects'} and set(new)-set(old)=={'declared_evidence_closure'})
ck('unchanged_46_helper_functions',sum(old[n]==new.get(n) for n in old)==46)
files=['incremental.py','inventory-books.py','production-render_books.py','production-validate.py','probe-preparation.py','probe-evidence-closure.py','root-technical-review.py']
evidence=['technical-delta-map.json','run-config.json','review-plan.json','baseline-proof.json']
for name,driver in [('p-323dd751/result.json','probe-preparation.py'),('p-f0ee8fee/result.json','probe-preparation.py'),('closure-probe-eff4992a/result.json','probe-evidence-closure.py')]:
    d=load(name);ck(name, d['run_id']==c['run_id'] and d['helper_sha256']==sha('incremental.py') and d['driver_sha256']==sha(driver) and d['completion_credit']==0 and all(d['checks'].values()))
    evidence.append(name)
total=0
for stem in ['hosea','joel','amos','obadiah','jonah','micah']:
    raw=(H/(stem+'-pinned-original.json')).read_bytes();original=json.loads(raw);seed=load(stem+'-seed.json');identity=load(stem+'-identity.json');inventory=load(stem+'-inventory.json');gate=load(stem+'-whole-book-source-reading-gate.json')
    blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    units=[u for ch in original['chapters'] for u in ch['verses']];saved=[u for ch in seed['chapters'] for u in ch['verses']]
    ck(stem+'/full_blob_identity',blob==identity['sha']==inventory['source_blob_sha'] and sha(stem+'-pinned-original.json')==inventory['source_raw_sha256'])
    ck(stem+'/all_source_fields_order',[{k:v for k,v in u.items() if k not in {'status','cross_references'}} for u in saved]==units)
    ck(stem+'/original_metadata',seed['source_metadata']['original_book_metadata']=={k:v for k,v in original.items() if k!='chapters'} and [ch['source_metadata'] for ch in seed['chapters']]==[{k:v for k,v in ch.items() if k!='verses'} for ch in original['chapters']])
    ck(stem+'/full_source_reading_gate',gate['source_references']==[u['reference'] for u in units] and gate['total_source_units']==len(units) and gate['source_commit']==c['source_commit'] and gate['baseline_commit']==c['baseline_commit'] and gate['completion_credit']==0)
    ck(stem+'/complete_gate_text',[(u['reference'],u['complete_text']) for u in gate['units']]==[(u['reference'],'\n'.join([u['text']]+u.get('continuation_paragraphs',[]))) for u in units])
    total+=len(units)
    evidence += ['inventory-'+stem+'-receipt.json',stem+'-whole-book-source-reading-gate.json']
ck('exact590_native_scope',total==590 and sum(len(p['source_references']) for p in load('review-plan.json')['packets'])==590)
receipt={
 'run_id':c['run_id'],'base_commit':c['baseline_commit'],'source_commit':c['source_commit'],
 'reviewed':c['date'],'review_timezone':'America/New_York','reviewer':'Independent technical peer Codex /root',
 'disposition':'accepted','outstanding_findings':[],'completion_credit':0,'repo_mutations':0,
 'files':[entry(n) for n in files],'evidence':[entry(n) for n in evidence],'independent_checks':checks,
 'review_scope':[
  'Read the complete helper delta against the previously accepted 0808 helper. Production renderer and validator are now used without mutation; 46 other helper functions preserve their accepted implementation.',
  'Inspected explicit transitive evidence closure, portable contained paths, file/hash bindings, cycle handling, final capture recheck and copy-time hash checks. Full source/target/rationale rereads remain archived through their explicit references.',
  'Read the complete sequential inventory delta and the relevant unchanged preservation implementation. Independently verified all six pinned raw blob identities, exact original fields, book/chapter metadata, complete source-reading gates and the 590-unit plan.',
  'Read both final six-book fixture drivers/results and all 19 closure rejection probes. Their semantic receipts are explicitly synthetic and receive zero review credit; actual renderer, validator, maintenance readback, historical objects and NT pointer are checked in scratch.',
  'No production code changes, broad fixture reruns, original-language claims or semantic review credit arise from this technical acceptance.'
 ],'review_outputs':['341538','0e8388','f99fc2','582224'],
 'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()
}
(H/'technical-peer-review.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'receipt_sha256':sha('technical-peer-review.json'),'completion_credit':0}))
