from pathlib import Path
from datetime import datetime,timezone
import json
import incremental as m
h=Path(__file__).resolve().parent
p=m.load(h/'helper-technical-proposal.json')
assert m.digest(h/'helper-technical-proposal.json')=='a0e615dfe23d4a481fe8e7f6e0fc8b72832507486ae8938a651f40eaf1dac68c'
assert m.digest(h/'technical-peer-review.json')==m.digest(h/'before-staged-audit-technical-peer-review.json.raw.txt')=='12194a62bb80db3cca4dc4f0d14d182aa5f477c7175f8cfb1aa2114a3bbd26a1'
old=m.load(h/'technical-peer-review.json')
before=(h/'before-staged-audit-incremental.py.raw.txt').read_text(encoding='utf-8')
after=(h/'incremental.py').read_text(encoding='utf-8')
added='''
def staged_readable_audit_inputs(outputs,stage,datasets):
    """Audit every freshly rendered view while keeping unchanged files out of writes."""
    audit_inputs=dict(outputs)
    for book,data in datasets.items():
        for name in [data['readable_html'],data['readable_text']]:
            path=slug(book)+'/'+name
            raw=safe_path(stage,path).read_bytes().replace(b'\\r\\n',b'\\n')
            if path in outputs:require(outputs[path]==raw,'Write/audit readable bytes differ: '+path)
            audit_inputs[path]=raw
    return audit_inputs
'''
assert after.count(added)==1
assert before.count('    audit_objects(datasets,progress,checksets,outputs)')==1
assert before.replace('    audit_objects(datasets,progress,checksets,outputs)','    audit_objects(datasets,progress,checksets,staged_readable_audit_inputs(outputs,stage,datasets))')==after.replace(added,'')
assert m.digest(h/'incremental.py')=='b915f6fb47c1c8f7714f8deeeb4ee5c29a5ce746036ac71435213ff664b12092'
for item in p['files']+p['evidence']:
    assert m.digest(h/item['file'])==item['sha256'],item
amendment=m.load(h/'staged-readable-audit-technical-amendment.json')
for item in amendment['prior_revision']+[amendment[k] for k in ['exact_diff','focused_probe','legacy_probe_with_current_helper']]:
    assert m.digest(h/item['file'])==item['sha256'],item
for name,script in [('staged-readable-audit-probe-result.json','probe-staged-readable-audit.py'),('pending-revisit-probe-result.json','probe-pending-revisit.py'),('staged-audit-legacy-source-sections-probe-result.json','probe-legacy-source-sections.py')]:
    probe=m.load(h/name)
    assert probe['result']=='passed' and probe['helper_sha256']==m.digest(h/'incremental.py') and probe['probe_sha256']==m.digest(h/script)
    assert probe['production_writes']==probe['completion_credit']==0
    if name=='staged-readable-audit-probe-result.json':
        assert all(v is True for v in probe['checks'].values())
        assert (probe['selected_source_units'],probe['new_completed_sources'],probe['new_completed_pairs'])==(128,115,123)
        assert probe['datasets']==m.REVIEW_BOOKS
assert (h/'production-render_books.py').read_bytes()==m.original('scripts/render_books.py')
assert (h/'production-validate.py').read_bytes()==m.original('scripts/validate.py')
assert m.digest(h/'source-registry.json')=='361750c1a002bf32b4fef155e6ddea2a0faa6345417e5a7b2ebde91debecb090'
result={'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'exact_additional_audit_mapping_and_one_callsite_verified':True,'unchanged_write_set_preserved':True,'no_missing_or_changed_readable_audit_bypass':True,'all_prior_helper_logic_unchanged':True,'production_scripts_unchanged':True,'current_helper_probe_identities_verified':True,'actual_nine_book_stage_audit_pass_and_negative_checks_reviewed':True,'semantic_packets_and_registry_unchanged':True,'completion_credit':0}
(h/'root-staged-audit-technical-result.json').write_bytes(m.encoded(result))
r={k:v for k,v in old.items() if k not in ['files','evidence','frozen_utc','review_outputs']}
r['files']=p['files']+[{'file':Path(__file__).name,'sha256':m.digest(Path(__file__))}]
r['evidence']=p['evidence']+[{'file':'helper-technical-proposal.json','sha256':m.digest(h/'helper-technical-proposal.json')},{'file':'root-staged-audit-technical-result.json','sha256':m.digest(h/'root-staged-audit-technical-result.json')}]
r['review_scope']=old['review_scope']+['Same-byte readable compatibility: separate audit mapping always supplies every freshly rendered view, preserving exact changed-file write set. Actual full-stage positive and corrupted-unchanged-view negative probes reviewed. Write/audit disagreement rejected; all prior helper logic and semantic inputs unchanged.']
r['review_outputs']=old['review_outputs']+['780cd8','02265a','212610']
r['frozen_utc']=datetime.now(timezone.utc).isoformat()
(h/'technical-peer-review.json').write_bytes(m.encoded(r))
m.declared_evidence_closure(['technical-peer-review.json'])
print(json.dumps({'accepted':True,'sha256':m.digest(h/'technical-peer-review.json'),'completion_credit':0}))
