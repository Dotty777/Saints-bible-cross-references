"""Freeze only a completely read, curated and separately reread current-run packet."""
from pathlib import Path
from datetime import datetime,timezone
import csv,hashlib,json,sys,re
from passages import INDEX,keys,complete_text
H=Path(__file__).parent;S=sys.argv[1]
def get(n):return json.loads((H/n).read_text(encoding='utf-8'))
def put(n,x):(H/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(n):return hashlib.sha256((H/n).read_bytes()).hexdigest()
C=get('run-config.json');P=next(p for p in get('review-plan-extension.json')['packets'] if p['stem']==S)
assert C['run_id']=='2026-10-31T215146Z' and not P.get('inventory_pending',False)
SEL=get(S+'-selection.json');refs=SEL['source_references'];source_data=get('before-'+re.sub('[^a-z0-9]+','-',P['book'].lower()).strip('-')+'__verses.json');chapter_by_ref={v['reference']:c['chapter'] for c in source_data['chapters'] for v in c['verses']};chapters=list(dict.fromkeys(chapter_by_ref[r] for r in refs));L=get(S+'-reading-log.json');G=get(S+'-source-reading-gate.json');T=get(S+'-reread.json');K=get(S+'-cases.json')
assert (L['run_id'],L['base_commit'],L['source_commit'])==(C['run_id'],C['baseline_commit'],C['source_commit'])
assert L['source_units_read_in_order']==refs==G['source_references']
assert set(K)=={'deferred_source_units','unresolved_candidates','unread_hints'}
supported={t['source_reference'] for t in T};deferred={c['source_reference'] for c in K['deferred_source_units']}
assert len(deferred)==len(K['deferred_source_units']) and not supported&deferred and supported|deferred==set(refs)
assert len({(t['source_reference'],t['target']) for t in T})==len(T)
with (H/(S+'.tsv')).open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f,delimiter='\t'))
assert rows==[{k:t[k] for k in ['source_reference','target','relationship','rationale']} for t in T]
for r,text in L['units'].items():assert text==complete_text(INDEX[r])
for p in L['context_references']:
 for r in keys(p):assert L['units'][r]==complete_text(INDEX[r])
for t in T:
 assert t in L['reread_versions'],'Final complete triple has not been separately acknowledged after reading.'
 assert t['source_text']==L['units'][t['source_reference']]
 assert [u['reference'] for u in t['target_units']]==keys(t['target'])
 assert t['relationship'].strip() and t['rationale'].strip()
 for u in t['target_units']:assert u['text']==L['units'][u['reference']]
for kind,cases in K.items():
 for c in cases:
  assert c['source_reference'] in refs and c['source_unit_read'] and c['source_text']==L['units'][c['source_reference']]
  assert c['completed_source_credit']==c['completed_pair_credit']==0 and c['reason'].strip()
  assert dict(kind=kind,case=c) in L['cases_reread'],'Final complete case has not been separately acknowledged after reading.'
  if kind=='unresolved_candidates':
   assert c['source_and_target_read'] and c['target_passage_read']
   assert [u['reference'] for u in c['target_units']]==keys(c['target'])
   for u in c['target_units']:assert u['text']==L['units'][u['reference']]
  if kind=='unread_hints':
   assert not c['target_passage_read'] and not c['source_and_target_read'] and not c.get('target_units')
   e=c['availability_evidence'];assert sha(e['file'])==e['sha256']
L['all_final_cases_read']=True;L['complete_source_target_rationale_triples_read']=True
L['all_retained_rationales_reread']=True
put(S+'-reading-log.json',L)
A=dict(run_id=C['run_id'],base_commit=C['baseline_commit'],source_commit=C['source_commit'],source_book=L['source_book'],source_chapters=chapters,source_references=refs,considered_source_references=SEL['considered_source_references'],selection_evidence={'file':S+'-selection.json','sha256':sha(S+'-selection.json')},reviewed=C['date'],review_timezone='America/New_York',reviewer=SEL.get('reviewer','Codex author /root/amos_author_recovery'),context_references=L['context_references'],source_units_read=len(refs),completed_source_verses=len(supported),completed_pairs=len(T),deferred_source_units=len(deferred),read_unretained_candidates=len(K['unresolved_candidates']),unread_hints=len(K['unread_hints']),actual_context_units=len(L['units']),tsv_file=S+'.tsv',tsv_sha256=sha(S+'.tsv'),cases_file=S+'-cases.json',cases_sha256=sha(S+'-cases.json'),reread_evidence={'file':S+'-reread.json','sha256':sha(S+'-reread.json')},reading_log={'file':S+'-reading-log.json','sha256':sha(S+'-reading-log.json')},source_reading_gate={'file':S+'-source-reading-gate.json','sha256':sha(S+'-source-reading-gate.json')},all_source_verses_read=True,all_target_passages_read=True,necessary_context_read=True,all_retained_rationales_reread=True,complete_source_target_rationale_triples_read=True,frozen_utc=datetime.now(timezone.utc).isoformat(),notes='Scope is only the selected pending-source reevaluation cohort. Every selected actual native source unit was read in order. Considered but unselected sources receive no substantive revisit or completion credit. Empty selected cohorts attest no substantive source or target review. Every retained target and necessary context was actually read this run. All final complete source/target/category/rationale triples and all final cases were separately reread and explicitly acknowledged. Deferred sources, unretained candidates and unread hints receive zero completion credit.')
put(S+'-review.json',A)
print(json.dumps(dict(author_sha256=sha(S+'-review.json'),tsv_sha256=A['tsv_sha256'],cases_sha256=A['cases_sha256'],source_units_read=len(refs),completed_source_verses=len(supported),completed_pairs=len(T),context_ranges=len(L['context_references']),context_units=len(L['units'])),indent=2))
