"""Only the current-run exclusion and native-section adaptations; no new semantic credit."""
import sys,json,hashlib,datetime
from pathlib import Path
H=Path(__file__).parent;sys.path.insert(0,str(H));import incremental as m
prior=m.load(H/'before-progress.json')['pending_evidence_review']['considered_source_references'];assert len(prior)==1124 and len(set(prior))==1124
assigned=[r for p in m.PLAN['packets'] for r in p['candidate_source_references']];assert len(assigned)==787 and len(set(assigned))==787 and not set(assigned)&set(prior)
assert assigned[0]=='Psalms 40:9'
for p in m.PLAN['packets']:assert p['candidate_source_references']==m.available_refs(p['book'])
psalm_pending=[v['reference'] for v in m.flat(m.book_data('Psalms')) if v['status']=='pending'];excluded=[r for r in psalm_pending if r in prior];assert len(excluded)==90 and len(m.available_refs('Psalms'))==269
old=m.selection
try:
 m.selection=lambda stem:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==stem)['candidate_source_references'][:20] if stem=='psalms-pending' else []}
 cursor=m.pending_cursor(m.load(H/'before-progress.json'),{s:{'cohort':[]} for s in m.STEMS},{})
 assert cursor['considered_source_units_this_run']==20 and cursor['actual_source_units_reread_this_run']==0 and len(cursor['considered_source_references'])==1144
 assert cursor['next_candidate']['reference']==assigned[20] and cursor['completion_credit_for_consideration_or_rereading']==0
 m.selection=lambda stem:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==stem)['candidate_source_references'][:1] if stem=='isaiah-pending' else []}
 try:m.considered_scope()
 except ValueError:pass
 else:raise AssertionError('Skipped prior canonical candidates accepted')
finally:m.selection=old
sirach=m.book_data('Sirach');prologue=next(c for c in sirach['chapters'] if any(v['reference']=='Sirach Prologue 1' for v in c['verses']));chapter_map={v['reference']:c['chapter'] for c in sirach['chapters'] for v in c['verses']};assert chapter_map['Sirach Prologue 1']==m.native_chapters('Sirach',['Sirach Prologue 1'])[0]
for n in ['book-author.py','freeze-book-author.py']:
 source=(H/n).read_text(encoding='utf-8');compile(source,n,'exec');assert "chapters=list(dict.fromkeys(chapter_by_ref[r] for r in refs))" in source
old_source=(H/'accepted-prior-incremental.py.raw.txt').read_text(encoding='utf-8');expected=old_source.replace("    old=previously_read_refs(book)\n    return [v['reference'] for v in flat(book_data(book)) if v['status']=='pending']","    old=previously_read_refs(book)\n    considered=set(load(HERE/'before-progress.json').get('pending_evidence_review',{}).get('considered_source_references',[]))\n    return [v['reference'] for v in flat(book_data(book)) if v['status']=='pending' and v['reference'] not in considered]")
assert expected==(H/'incremental.py').read_text(encoding='utf-8')
result={'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'helper_sha256':m.digest(H/'incremental.py'),'probe_sha256':m.digest(Path(__file__)),'result':'passed','prior_considered_count':1124,'assigned_unconsidered_candidates':787,'excluded_prior_considered_pending_psalms':90,'initial_cursor':assigned[0],'partial20_cursor':cursor['next_candidate'],'sirach_prologue_native_chapter':prologue['chapter'],'previous_cursor_references_preserved':True,'reject_later_packet_before_prior_candidates':True,'only_helper_change_is_excluding_previously_considered_candidates':True,'all_previous_preservation_and_compatibility_logic_unchanged':True,'production_writes':0,'completion_credit':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'current-run-adaptation-probe-result.json').write_bytes(m.encoded(result));print(json.dumps(result,indent=2))
