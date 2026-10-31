from pathlib import Path
import hashlib,json,subprocess
from copy import deepcopy
H=Path(__file__).resolve().parent;R=H.parent/'saints-crossrefs'
C=json.loads((H/'run-config.json').read_text(encoding='utf-8'))
BASE=C['baseline_commit'];PIN=C['source_commit'];RUN=C['run_id'];DATE=C['date']
BEFORE=json.loads((H/'before-progress.json').read_text(encoding='utf-8-sig'))
PRIOR=[b['records'].strip('/') for b in BEFORE['books'] if b['status']=='completed']
OLD_FOLDERS=[b['records'].strip('/') for b in BEFORE['books'] if b.get('total_source_verse_units') is not None]
FOLDERS=OLD_FOLDERS+[b['folder'] for b in C['books'] if b['new']]
CONTINUATION_FOLDERS=[f for f in OLD_FOLDERS if f not in PRIOR and f not in {b['folder'] for b in C['books']}]
load=lambda q:json.loads(Path(q).read_text(encoding='utf-8-sig'))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
gsha=lambda raw:hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
flat=lambda d:[v for c in d['chapters'] for v in c['verses']]
def git(*a):return subprocess.check_output(['git',*a],cwd=R,stderr=subprocess.PIPE)
def old(path):return json.loads(git('show',BASE+':'+path))
def require(ok,msg):
 if not ok:raise AssertionError(msg)
def required_paths():
 paths={'canon.json','progress.json',f'review-batches/{RUN}.json'}
 paths.update(f+'/'+name for f in FOLDERS for name in ['verses.json','source-checks.json'])
 paths.update(f+'/inventory.json' for f in FOLDERS if f!='genesis')
 paths.update(b['folder']+'/review-batches/'+RUN+'.json' for b in C['books'])
 require(len(paths)==3+3*len(FOLDERS)-1+len(C['books']),'Complete remote JSON coverage differs')
 return paths

def unavailable_hint_target(hint):
 target=hint.get('target',hint.get('unavailable_reference_text'))
 require(isinstance(target,str) and bool(target.strip()),'Unavailable target locator missing')
 if 'target' in hint and 'unavailable_reference_text' in hint:require(hint['target']==hint['unavailable_reference_text'],'Conflicting unavailable locators')
 return target

def unavailable_hint_groups(authors,packets):
 groups=[]
 def bound_json(record,field):
  name=record[field];expected=record.get(field[:-5]+'_sha256') or record.get(field+'_sha256');path=H/name
  require(path.resolve().parent==H.resolve() and path.is_file() and bool(expected) and sha(path.read_bytes())==expected,'Unavailable-source evidence binding differs')
  return load(path),{'file':name,'sha256':expected}
 for stem,author in authors.items():
  hints=deepcopy(author.get('unavailable_locator_hints',[])+author.get('unavailable_target_hints',[]));proof=[]
  # B preserves absent native-unit locators in its hash-bound reading attestation.
  if 'reading_attestation_file' in author:
   attestation,attestation_binding=bound_json(author,'reading_attestation_file')
   if 'unavailable_reference_hints_file' in attestation:
    bundle,bundle_binding=bound_json(attestation,'unavailable_reference_hints_file')
    require(isinstance(bundle,dict) and isinstance(bundle.get('unavailable_reference_hints'),list),'Unavailable hint bundle is malformed')
    hints.extend(deepcopy(bundle['unavailable_reference_hints']));proof.extend([attestation_binding,bundle_binding])
  if not hints:continue
  seen=set()
  for hint in hints:
   require(hint['source_reference'] in packets[stem]['cohort'],'Unavailable hint source outside reviewed packet')
   pair=(hint['source_reference'],unavailable_hint_target(hint));require(pair not in seen,'Duplicate unavailable hint');seen.add(pair)
   readflags=[hint[k] for k in ['target_passage_read','target_text_read','source_and_target_body_read'] if k in hint]
   require(bool(readflags) and all(v is False for v in readflags),'Unavailable target incorrectly marked read')
   if 'source_and_target_body_read' in hint:require(hint.get('body_available_in_exact_inventory') is False,'Combined unread flag lacks explicit absent-body evidence')
   require(hint['completed_source_credit']==hint['completed_pair_credit']==0 and hint.get('retained',False) is False and hint.get('identity_resolved',False) is False,'Unavailable hint incorrectly credited or resolved')
   require(not hint.get('target_verses') and not hint.get('target_text'),'Unavailable target body fabricated')
   require(all(pair!=(r['source_reference'],r['target']) for r in packets[stem]['rows']+packets[stem]['candidates']),'Unavailable hint counted as a retained pair or read candidate')
  for field in ['unavailable_source_check_file','unavailable_target_hints_file']:
   if field in author:
    _,binding=bound_json(author,field);proof.append(binding)
  require(bool(proof),'Unavailable hint has no bound availability record')
  filename=stem+'-review.json'
  groups.append({'packet':stem,'author_receipt_file':filename,'author_receipt_sha256':sha((H/filename).read_bytes()),'hints':hints,'availability_records':proof,'completed_source_credit':0,'completed_pair_credit':0,'read_target_candidate_credit':0})
 return groups

def unavailable_hint_note(groups):
 if not groups:return None
 locators='; '.join(h['source_reference']+' -> '+unavailable_hint_target(h) for g in groups for h in g['hints'])
 return ('Run '+RUN+': Unavailable target locator hints remain pending and unread, with zero source, pair and read-candidate credit: '+locators+'. Exact hints, frozen author receipts and availability records are preserved in review-batches/'+RUN+'.json and its input archive. These hints are excluded from retained pairs, read target candidates and inventory credit.')
