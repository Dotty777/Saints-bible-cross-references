from pathlib import Path
import runpy,json
from publication_parent import PUBLICATION_PARENT,publication_contract
publication=publication_contract()
H=Path(__file__).resolve().parent;C=runpy.run_path(str(H/'audit-common.py'))
for name in ['review_contract.py','finalize-reviews.py','integrate.py','audit-common.py','preservation-audit.py','run_support.py','publication_parent.py']:compile((H/name).read_text(encoding='utf-8'),name,'exec')
out={'repository':'Dotty777/Saints-bible-cross-references-','run_id':C['RUN'],'baseline_commit':C['BASE'],'files':sorted(C['required_paths']()),'completion_credit':0,'readback_requirement':'Fetch fresh MCP identities at the published main commit, then parse each complete exact Git blob and compare the full JSON. An empty MCP body for a large object is not an empty dataset.'}
out.update(review_base_commit=C['BASE'],publication_parent=PUBLICATION_PARENT,preserved_nt_tree_git_sha=publication['preserved_nt_tree_git_sha'],concurrent_unchanged_git_objects=[{'path':x['path'],'git_blob':x['git_blob']} for x in publication['complete_concurrent_objects'] if x['path'] in publication['added_paths']],concurrent_preservation_requirement='Verify the published commit descends from publication_parent and retains the exact entire NT tree and both NT script Git blobs. This separate identity proof adds no OT JSON paths, source reviews or completion credit.')
(H/'readback-required-paths.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'compiled':True,'required_remote_json_objects':len(out['files']),'repository_mutations':0}))
