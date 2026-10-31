from pathlib import Path
import ast,hashlib,json,datetime
H=Path(__file__).resolve().parent
load=lambda n:json.loads((H/n).read_bytes())
sha=lambda n:hashlib.sha256((H/n).read_bytes()).hexdigest()
entry=lambda n:{'file':n,'sha256':sha(n)}
c=load('run-config.json');checks=dict(load('root-inventory-technical-result.json')['checks'])
def ck(n,v):
 assert v,n
 checks[n]=True
def funcs(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text(encoding='utf-8-sig')).body if isinstance(n,ast.FunctionDef)}
old=funcs(H.parent/'hourly-2026-10-31-1002/incremental.py');new=funcs(H/'incremental.py')
ck('bounded_helper_delta',{n for n in old if old[n]!=new.get(n)}=={'reviewed_code','prepare','capture_maintenance'} and set(new)-set(old)=={'following_source_review'})
ck('unchanged47_helper_functions',sum(old[n]==new.get(n) for n in old)==47)
probe=load('end-of-ot-probe-result.json')
ck('probe_current_identity',probe['run_id']==c['run_id'] and probe['result']=='passed' and probe['completion_credit']==probe['new_completed_source_credit']==probe['new_pair_credit']==0)
for field in ['helper_reference','renderer_reference','validator_reference']:
 item=probe[field];ck('probe_hash/'+field,sha(item['file'])==item['sha256'])
for field in ['new_testament_source_rejected','unread_malachi_with_null_pointer_rejected','exact_unread_malachi_pointer_accepted','all_fixture_scripture_and_source_check_bytes_preserved_by_renderer','historical_source_target_bodies_and_anchors_preserved','unaccepted_technical_receipt_rejected','wrong_run_technical_receipt_rejected','stale_helper_renderer_validator_digests_rejected','exact_technically_bound_proposed_code_bytes_captured']:
 ck('focused_probe/'+field,probe[field] is True)
files=['incremental.py','inventory-books.py','production-render_books.py','production-validate.py','probe-end-of-ot.py','root-inventory-technical-check.py','root-freeze-technical-review.py']
evidence=['run-config.json','review-plan.json','baseline-proof.json','helper-technical-proposal.json','source-review-gates.json','preceding-micah-source-reading-gate.json','root-inventory-technical-result.json','end-of-ot-probe-result.json']
for stem in ['nahum','habakkuk','zephaniah','haggai','zechariah','malachi']:evidence+=['inventory-'+stem+'-receipt.json',stem+'-whole-book-source-reading-gate.json']
r={'run_id':c['run_id'],'base_commit':c['baseline_commit'],'source_commit':c['source_commit'],'reviewed':c['date'],'review_timezone':'America/New_York','reviewer':'Independent technical peer Codex /root','disposition':'accepted','outstanding_findings':[],'completion_credit':0,'repo_mutations':0,'files':[entry(n) for n in files],'evidence':[entry(n) for n in evidence],'independent_checks':checks,'review_scope':[
'Read the complete helper changes against the previously accepted 1002 helper; 47 other functions remain unchanged. End-of-OT continuation is null, preserving earliest pending and avoiding implicit New Testament source review.',
'Read the renderer and validator changes: readable end-of-OT labels and separate never-reviewed continuation checks. Scratch probes reject null when an unread unit remains and reject a New Testament continuation; preserve earlier source/target text, anchors, counts and pending status.',
'Found and requested correction of baseline-only code capture. Reviewed the exact fix and focused rejection probes: proposed production code requires final independent technical acceptance binding run/base/source/helper/renderer/validator. Preparation stages those exact bound bytes.',
'Independently verified all six inventories against complete pinned raw Git blobs, native metadata, fields and order, whole-book source-reading gates and exact 460-unit plan. Checked reused Micah evidence byte-for-byte against exact published Git objects, with zero current reading credit.',
'This technical receipt supplies no completed source or pair credit and makes no semantic review or original-language claims. Semantic acceptance remains the separate author and independent peer evidence.'
],'review_outputs':['b2297f','f7e24f','e4b6be','518f1d','05e658','eed282','d0a64b','e85673'],'frozen_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'technical-peer-review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'checks':len(checks),'technical_receipt_sha256':sha('technical-peer-review.json'),'completion_credit':0}))
