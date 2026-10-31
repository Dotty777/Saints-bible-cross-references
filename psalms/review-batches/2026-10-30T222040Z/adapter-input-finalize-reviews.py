"""Validate frozen evidence and write only three scratch preflight artifacts."""
from datetime import datetime,timezone
import json,runpy
from review_contract import HERE,DATE,RUN,validate_packets

def save(name,value):
 (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

plan=validate_packets()
assert (plan["first_reviewed_source_units"],plan["revisited_source_units_read"],plan["source_units_read"])==(672,0,672)
assert set(plan["books"])=={"Psalms"} and not plan["books"]["Psalms"]["revisit_cohort"]
preflight={'run_id':RUN,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'source_units':len(plan['supported']),'source_units_read':plan['source_units_read'],'deferred_source_units':len(plan['deferred']),'reviewed_dates':[DATE],'retained_pairs':len(plan['rows']),'reference_resolution':'passed in actual source order','canonical_target_membership':'passed','no_duplicate_self_pairs':'passed','same_chapter_labels':'passed','final_peer_input_and_author_receipt_hash_bindings':'passed','all_declared_author_and_peer_pin_metadata_and_raw_hashes':'passed','all_historical_stage_exact_old_new_deltas':'passed','supported_plus_deferred_exact_actual_source_cohort':'passed','new_unresolved_identity_candidates_excluded':len(plan['candidates']),'source_deferrals_separate_from_target_candidates':True,'inventory_completion_credit':0,'completion_credit':0}
hint_contract=runpy.run_path(str(HERE/'audit-common.py'))
hintgroups=hint_contract['unavailable_hint_groups'](plan['authors'],plan['packets'])
preflight['unavailable_target_locator_hint_count']=sum(len(g['hints']) for g in hintgroups)
preflight['unavailable_locator_hints_are_unread']=True
preflight['unavailable_locator_hint_completion_credit']=0
preflight['historical_filename_bindings']=plan['historical_filename_bindings']
preflight['first_reviewed_source_units']=plan['first_reviewed_source_units']
preflight['revisited_source_units_read']=plan['revisited_source_units_read']
preflight['rereading_completion_credit']=0
preflight['revisit_policy']='This run reviews only the 672 newly encountered source units in Psalms 81–117. No earlier source is revisited; inventory, rereading and unresolved evidence receive zero completion credit.'
save('applied-corrections.json',plan['fixes'])
save('receipt-fingerprints.json',plan['fingerprints'])
save('target-identity-preflight.json',preflight)
print(json.dumps({'new_source_verses':len(plan['supported']),'new_pairs':len(plan['rows']),'source_units_read':plan['source_units_read'],'deferred_source_units':len(plan['deferred']),'target_met':len(plan['rows'])>=500,'target_excess':max(0,len(plan['rows'])-500),'new_uncounted_target_candidates':len(plan['candidates']),'author_and_peer_receipts_preserved_byte_for_byte':True}))
