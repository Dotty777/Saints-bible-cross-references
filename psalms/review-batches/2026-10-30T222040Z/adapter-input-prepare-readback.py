from pathlib import Path
import runpy,json
H=Path(__file__).resolve().parent;C=runpy.run_path(str(H/'audit-common.py'))
for name in ['review_contract.py','finalize-reviews.py','integrate.py','audit-common.py','preservation-audit.py']:compile((H/name).read_text(encoding='utf-8'),name,'exec')
out={'repository':'Dotty777/Saints-bible-cross-references-','run_id':C['RUN'],'baseline_commit':C['BASE'],'files':sorted(C['required_paths']()),'completion_credit':0,'readback_requirement':'Fetch fresh MCP identities at the published main commit, then parse each complete exact Git blob and compare the full JSON. An empty MCP body for a large object is not an empty dataset.'}
(H/'readback-required-paths.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'compiled':True,'required_remote_json_objects':len(out['files']),'repository_mutations':0}))
