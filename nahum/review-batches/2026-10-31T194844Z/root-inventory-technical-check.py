from pathlib import Path
import ast,hashlib,json,subprocess
H=Path(__file__).resolve().parent;R=H.parent/'saints-crossrefs'
load=lambda n:json.loads((H/n).read_bytes())
sha=lambda n:hashlib.sha256((H/n).read_bytes()).hexdigest()
c=load('run-config.json');checks={}
def ck(n,v):
 assert v,n
 checks[n]=True
previous=load('preceding-micah-source-reading-gate.json')
for item in previous['published_evidence']:
 raw=subprocess.check_output(['git','show',item['git_commit']+':'+item['repository_path']],cwd=R)
 ck('published/'+item['file'],item['git_commit']==c['baseline_commit'] and raw==(H/item['file']).read_bytes() and hashlib.sha256(raw).hexdigest()==item['sha256'])
for name,field in [('verses','baseline_verses_sha256'),('source-checks','baseline_checks_sha256')]:
 raw=subprocess.check_output(['git','show',c['baseline_commit']+':micah/'+name+'.json'],cwd=R)
 ck('preceding_micah/'+name,hashlib.sha256(raw).hexdigest()==previous[field])
ck('historical_zero_credit',previous['completion_credit']==previous['current_run_source_reading_credit']==0)
total=0
for stem in ['nahum','habakkuk','zephaniah','haggai','zechariah','malachi']:
 raw=(H/(stem+'-pinned-original.json')).read_bytes();original=json.loads(raw);seed=load(stem+'-seed.json');identity=load(stem+'-identity.json');inventory=load(stem+'-inventory.json');gate=load(stem+'-whole-book-source-reading-gate.json')
 blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
 units=[u for ch in original['chapters'] for u in ch['verses']];saved=[u for ch in seed['chapters'] for u in ch['verses']]
 ck(stem+'/full_blob_identity',blob==identity['sha']==inventory['source_blob_sha'] and sha(stem+'-pinned-original.json')==inventory['source_raw_sha256'])
 ck(stem+'/all_source_fields_order',[{k:v for k,v in u.items() if k not in {'status','cross_references'}} for u in saved]==units)
 ck(stem+'/original_metadata',seed['source_metadata']['original_book_metadata']=={k:v for k,v in original.items() if k!='chapters'} and [ch['source_metadata'] for ch in seed['chapters']]==[{k:v for k,v in ch.items() if k!='verses'} for ch in original['chapters']])
 ck(stem+'/full_source_reading_gate',gate['source_references']==[u['reference'] for u in units] and gate['total_source_units']==len(units) and gate['source_commit']==c['source_commit'] and gate['baseline_commit']==c['baseline_commit'] and gate['completion_credit']==0)
 ck(stem+'/complete_gate_text',[(u['reference'],u['complete_text']) for u in gate['units']]==[(u['reference'],'\n'.join([u['text']]+u.get('continuation_paragraphs',[]))) for u in units])
 receipt=load('inventory-'+stem+'-receipt.json')
 preceding=receipt['preceding_source_reading_gate']
 ck(stem+'/prior_inventory_gate',sha(preceding['file'])==preceding['sha256'] and preceding['all_prior_book_units_read'])
 total+=len(units)
ck('exact460_native_scope',total==460 and sum(len(p['source_references']) for p in load('review-plan.json')['packets'])==460)
canon=load('before-canon.json')
progress=load('before-progress.json')
ck('final_six_OT_order',[b['book'] for b in progress['books'][-6:]]==c['source_book_sequence'] and len(progress['books'])==43)
result={'run_id':c['run_id'],'checks':checks,'completion_credit':0,'new_semantic_review_credit':0,'production_mutations':0,'verifier_file':'root-inventory-technical-check.py','verifier_sha256':sha('root-inventory-technical-check.py')}
(H/'root-inventory-technical-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,indent=2))
