from pathlib import Path
import sys,json,datetime
H=Path(__file__).parent;sys.path.insert(0,str(H));import incremental as m
base=m.load(H/'review-plan.json');ext=m.load(H/'review-plan-extension.json');prior=m.load(H/'before-progress.json');assert base['candidate_count']==787 and ext['candidate_count']==343 and m.PLAN['candidate_count']==1130
assert m.digest(H/'incremental.py')=='b018228df0023f73321808176068618409e3ae0abf0220d0fcf53580bab7927c'
assert ext['extends_plan']=={'file':'review-plan.json','sha256':m.digest(H/'review-plan.json')}
assigned=[r for p in m.PLAN['packets'] for r in p['candidate_source_references']];assert len(assigned)==len(set(assigned))==1130 and not set(assigned)&set(prior['pending_evidence_review']['considered_source_references'])
for p in m.PLAN['packets']:assert p['candidate_source_references']==m.available_refs(p['book'])
for stem in ['proverbs-pending','isaiah-pending','jeremiah-pending']:
 if (H/(stem+'-review.json')).exists():m.receipt(stem)
old=m.selection
try:
 m.selection=lambda stem:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==stem)['candidate_source_references']}
 allcursor=m.pending_cursor(prior,{s:{'cohort':[]} for s in m.STEMS},{})
 assert allcursor['next_candidate'] is None and allcursor['considered_source_units_this_run']==1130 and len(allcursor['considered_source_references'])==2254 and allcursor['actual_source_units_reread_this_run']==0
 m.selection=lambda stem:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==stem)['candidate_source_references'][:20] if stem=='psalms-pending' else []}
 partial=m.pending_cursor(prior,{s:{'cohort':[]} for s in m.STEMS},{})
 assert partial['next_candidate']['reference']=='Psalms 47:6' and partial['completion_credit_for_consideration_or_rereading']==0
 m.selection=lambda stem:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==stem)['candidate_source_references'][:1] if stem=='ezekiel-pending' else []}
 try:m.considered_scope()
 except ValueError:pass
 else:raise AssertionError('Extension skip-ahead accepted')
finally:m.selection=old
for src,dst in [('book-author.py','extension-book-author.py'),('freeze-book-author.py','extension-freeze-book-author.py')]:
 expected=(H/src).read_text(encoding='utf-8').replace("get('review-plan.json')['packets']","get('review-plan-extension.json')['packets']");assert expected==(H/dst).read_text(encoding='utf-8');compile(expected,dst,'exec')
result={'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'result':'passed','helper_sha256':m.digest(H/'incremental.py'),'probe_sha256':m.digest(Path(__file__)),'original_plan_sha256':m.digest(H/'review-plan.json'),'extension_sha256':m.digest(H/'review-plan-extension.json'),'original_candidates':787,'extension_candidates':343,'combined_candidates':1130,'final_considered_fixture_count':2254,'all_considered_fixture_next_candidate':None,'partial20_next_candidate':partial['next_candidate'],'canonical_extension_skip_ahead_rejected':True,'existing_frozen_author_receipts_unchanged_validated':True,'separate_extension_tools_only_change_plan_filename':True,'production_writes':0,'completion_credit':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'current-extension-probe-result.json').write_bytes(m.encoded(result));print(json.dumps(result,indent=2))
