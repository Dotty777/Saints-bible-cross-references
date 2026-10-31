"""Strict read-only boundary between the review base and concurrent publication parent."""
from pathlib import Path
import hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;R=H.parent/'saints-crossrefs'
REVIEW_BASE='e194517a8bdc5ceaba07142d7eafdc726480dd2c'
PUBLICATION_PARENT='0bed9c182097eb0e681d4b49e09a3de2b814ab98'
CONTRACT_FILE='publication-parent2-reconciliation.json'
CONTRACT_SHA256='6edcd209313b722d4fa07793c78b82d64cf73b2c70d8a07f665132169daa227d'
MUTABLE_OT_PROGRESS_FIELDS={'updated','updated_at_utc','books','runs','completed_source_verses','completed_cross_references','completed_chapters','completed_book_records','pending_book_records','next','next_unreviewed'}
git=lambda *a:subprocess.check_output(['git',*a],cwd=R,stderr=subprocess.PIPE)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
gsha=lambda raw:hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
def tree(commit):
 return {line.split('\t',1)[1]:tuple(line.split('\t',1)[0].split()) for line in git('ls-tree','-r',commit).decode().splitlines()}
def bound_local(name,expected):
 p=(H/name).resolve();assert p.is_relative_to(H.resolve()) and p.is_file() and not p.is_symlink(),name
 assert sha(p.read_bytes())==expected,(name,'bound bytes changed');return p
def validate_progress_metadata(value,parent):
 assert {k:v for k,v in value.items() if k not in MUTABLE_OT_PROGRESS_FIELDS}=={k:v for k,v in parent.items() if k not in MUTABLE_OT_PROGRESS_FIELDS},'Unowned root progress metadata changed'
 assert value['new_testament_tracker']==parent['new_testament_tracker'],'Concurrent NT pointer changed'
def validate_readme_metadata(value,contract):
 value=value.replace('\r\n','\n')
 for stem in ['readme_preserved_block','readme_preserved_coverage']:
  expected=bound_local(contract[stem+'_file'],contract[stem+'_sha256']).read_text(encoding='utf-8')
  assert value.count(expected)==1,'Concurrent README prose missing, changed or duplicated'
def validate_output_scope(outputs,contract):
 folded=set()
 protected={p.casefold() for p in contract['added_paths']}
 for path in outputs:
  assert isinstance(path,str) and path and not path.startswith('/') and '\\' not in path,'Noncanonical output path'
  parts=path.split('/')
  assert all(part not in ['', '.', '..'] and re.fullmatch(r'[A-Za-z0-9_.-]+',part) and not part.endswith(('.', ' ')) for part in parts),'Noncanonical output component'
  assert all(part.split('.')[0].casefold() not in {'con','prn','aux','nul',*[f'com{i}' for i in range(1,10)],*[f'lpt{i}' for i in range(1,10)]} for part in parts),'Reserved Windows output component'
  key=path.casefold();assert key not in folded,'Case-folded output collision';folded.add(key)
  assert key!='new-testament' and not key.startswith('new-testament/') and key not in protected,'Concurrent NT path included in outputs'
  assert key!='canon.json','Publication-parent canon must remain unchanged'
  assert key!='progress.json' or path=='progress.json','Noncanonical progress alias'
 if 'progress.json' in outputs:validate_progress_metadata(json.loads(outputs['progress.json']),load(H/'publication-parent2-progress.json'))
def publication_contract():
 c=load(bound_local(CONTRACT_FILE,CONTRACT_SHA256));config=load(H/'run-config.json')
 assert c['review_base']==config['baseline_commit']==REVIEW_BASE and c['publication_parent']==PUBLICATION_PARENT
 assert c['run_id']==config['run_id'] and c['source_commit']==config['source_commit'] and c['completion_credit']==c['semantic_review_credit']==c['repository_mutations']==0
 assert git('merge-base','--is-ancestor',REVIEW_BASE,PUBLICATION_PARENT)==b''
 old=tree(REVIEW_BASE);new=tree(PUBLICATION_PARENT)
 changed=sorted(p for p in old if new.get(p)!=old[p]);added=sorted(set(new)-set(old))
 assert changed==c['changed_existing_paths']==['README.md','canon.json','progress.json']
 assert added==c['added_paths'] and len(added)==65 and all(p.startswith('new-testament/') or p in ['scripts/render_new_testament.py','scripts/validate_new_testament.py'] for p in added)
 assert len(old)-3==c['unchanged_preexisting_path_count'] and all(new[p][:2]==('100644','blob') for p in changed+added)
 assert [x['path'] for x in c['complete_concurrent_objects']]==sorted(changed+added)
 for item in c['complete_concurrent_objects']:
  raw=git('cat-file','blob',new[item['path']][2]);assert gsha(raw)==item['git_blob']==new[item['path']][2] and sha(raw)==item['raw_sha256'] and len(raw)==item['bytes']
  if item['path'].endswith('.json'):json.loads(raw)
 for item in c['root_snapshots']:
  raw=bound_local(item['snapshot_file'],item['snapshot_sha256']).read_bytes()
  assert raw==git('cat-file','blob',item['git_blob']) and item['git_blob']==new[item['path']][2]
 assert {x['path'] for x in c['root_snapshots']}==set(changed)
 before=load_bytes(REVIEW_BASE,'progress.json');parent=load(H/'publication-parent2-progress.json')
 assert parent=={**before,'new_testament_tracker':c['new_testament_root_pointer']}
 original=load_bytes(REVIEW_BASE,'canon.json');canon=load(H/'publication-parent2-canon.json')
 assert canon=={**original,**{k:v['after'] for k,v in c['root_canon_metadata_changes'].items()}}
 assert set(c['root_canon_metadata_changes'])=={'review_scope','updated'} and all(original[k]==v['before'] for k,v in c['root_canon_metadata_changes'].items())
 assert git('rev-parse',PUBLICATION_PARENT+':new-testament').decode().strip()==c['preserved_nt_tree_git_sha']
 validate_readme_metadata((H/'publication-parent2-README.md').read_text(encoding='utf-8'),c)
 return c
def load_bytes(commit,path):return json.loads(git('show',commit+':'+path))
def require_parent_ready(contract):
 assert git('rev-parse','HEAD').decode().strip()==git('rev-parse','origin/main').decode().strip()==git('ls-remote','origin','refs/heads/main').decode().split()[0]==PUBLICATION_PARENT,'Publication parent moved or checkout has not advanced'
 assert not git('status','--porcelain').strip(),'Publication checkout is not clean'
 assert load(R/'progress.json')==load(H/'publication-parent2-progress.json'),'Publication-parent progress differs'
 return verify_concurrent_worktree(contract)
def verify_concurrent_worktree(contract):
 """Git-content identity permits checkout newline conversion, never content changes."""
 items={x['path']:x for x in contract['complete_concurrent_objects']}
 result=[]
 for path in contract['added_paths']+['canon.json']:
  p=R/path;assert p.is_file() and not p.is_symlink(),path
  original=git('cat-file','blob',items[path]['git_blob']);raw=p.read_bytes()
  assert gsha(original)==items[path]['git_blob'] and raw.replace(b'\r\n',b'\n')==original.replace(b'\r\n',b'\n'),path+' changed beyond checkout newline conversion'
  result.append({'path':path,'git_blob':items[path]['git_blob'],'working_copy_sha256':sha(raw),'git_blob_sha256':sha(original),'equal_after_checkout_newline_normalization':True})
 validate_progress_metadata(load(R/'progress.json'),load(H/'publication-parent2-progress.json'))
 validate_readme_metadata((R/'README.md').read_text(encoding='utf-8-sig'),contract)
 return result
def verify_published_tree(commit,contract):
 assert git('merge-base','--is-ancestor',PUBLICATION_PARENT,commit)==b'','Publication parent absent from ancestry'
 assert git('rev-parse',commit+':new-testament').decode().strip()==contract['preserved_nt_tree_git_sha'],'Published NT subtree changed'
 for x in contract['complete_concurrent_objects']:
  if x['path'] in contract['added_paths'] or x['path']=='canon.json':assert git('rev-parse',commit+':'+x['path']).decode().strip()==x['git_blob'],'Published concurrent Git object changed: '+x['path']
 return {'publication_parent':PUBLICATION_PARENT,'nt_tree_git_sha':contract['preserved_nt_tree_git_sha'],'unchanged_added_git_objects':len(contract['added_paths']),'completion_credit':0}
