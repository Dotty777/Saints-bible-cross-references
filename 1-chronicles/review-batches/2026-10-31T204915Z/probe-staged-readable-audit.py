"""Use the actual failed preflight stage to test unchanged-readable auditing; H writes only."""
from pathlib import Path
import sys,json,hashlib,datetime
H=Path(__file__).parent;sys.path.insert(0,str(H));import incremental as m
stage=H/'prepared-64654ac406824b20a366ee76a53cf8f0'
assert stage.is_dir()
datasets={b:m.load(stage/(m.slug(b)+'/verses.json')) for b in m.REVIEW_BOOKS}
checksets={b:m.load(stage/(m.slug(b)+'/source-checks.json')) for b in m.REVIEW_BOOKS}
progress=m.load(stage/'progress.json')
unchanged='1-chronicles/'+datasets['1 Chronicles']['readable_text']
assert (stage/unchanged).read_bytes().replace(b'\r\n',b'\n')==(m.REPO/unchanged).read_bytes().replace(b'\r\n',b'\n')
# Reconstruct only changed readable outputs as the real prepare path does.
writes={}
for b,d in datasets.items():
 for name in [d['readable_html'],d['readable_text']]:
  p=m.slug(b)+'/'+name;raw=(stage/p).read_bytes().replace(b'\r\n',b'\n');current=(m.REPO/p).read_bytes().replace(b'\r\n',b'\n')
  if raw!=current:writes[p]=raw
before=dict(writes);assert unchanged not in writes
views=m.staged_readable_audit_inputs(writes,stage,datasets)
assert writes==before and unchanged not in writes and unchanged in views
m.audit_objects(datasets,progress,checksets,views)
checks={'unchanged_readable_excluded_from_production_writes':True,'unchanged_fresh_readable_included_in_audit':True,'real_full_batch_audit_passed':True,'audit_mapping_does_not_mutate_write_set':True}
corrupt=dict(views);unit=next(v for v in m.flat(datasets['1 Chronicles']) if v['status']=='completed');needle=(unit['reference']+'\n'+m.complete_text(unit)+'\n').encode();assert needle in corrupt[unchanged];corrupt[unchanged]=corrupt[unchanged].replace(needle,b'CORRUPTED SOURCE\n',1)
try:m.audit_objects(datasets,progress,checksets,corrupt)
except ValueError as e:
 assert 'Readable complete source missing' in str(e);checks['actual_audit_rejects_corrupt_unchanged_readable']=True
else:raise AssertionError('Corrupt unchanged readable passed')
mismatch=dict(writes);mismatch[unchanged]=b'WRONG WRITTEN BYTES'
try:m.staged_readable_audit_inputs(mismatch,stage,datasets)
except ValueError as e:
 assert 'Write/audit readable bytes differ' in str(e);checks['rejects_write_audit_view_divergence']=True
else:raise AssertionError('Write/audit mismatch passed')
result={'run_id':m.RUN,'helper_sha256':m.digest(H/'incremental.py'),'probe_sha256':m.digest(Path(__file__)),'result':'passed','actual_preflight_stage':str(stage),'datasets':list(datasets),'selected_source_units':progress['runs'][-1]['source_units_read'],'new_completed_sources':progress['runs'][-1]['resolved_source_deferrals_count'],'new_completed_pairs':progress['runs'][-1]['new_completed_pairs'],'checks':checks,'production_writes':0,'completion_credit':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'staged-readable-audit-probe-result.json').write_bytes(m.encoded(result));print(json.dumps(result,indent=2))
