"""Read-only gates for this continuing ordered Old Testament source review.

Frozen receipts are inputs. Variants are adapted here without rewriting them.
Source deferrals have no target and never enter target-candidate resolution.
"""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import csv, hashlib, json
from passages import INDEX, keys, complete_text
from pin_artifact_contract import validated_pin_artifacts, checked_local, declared_pin_metadata

HERE=Path(__file__).resolve().parent
REPO=HERE.parent/'saints-crossrefs'
CONFIG=json.loads((HERE/'run-config.json').read_text(encoding='utf-8'))
RUN=CONFIG['run_id'];DATE=CONFIG['date'];PIN=CONFIG['source_commit'];BASE_COMMIT=CONFIG['baseline_commit']
BOOK_CONFIG={b['book']:b for b in CONFIG['books']}
GROUPS={b['book']:(b['folder'],list(b['packets']),None) for b in CONFIG['books']}
PACKET_CHAPTERS={s:cc for b in CONFIG['books'] for s,cc in b['packets'].items()}
REVISITS=CONFIG.get('revisit_packets',{})
assert not REVISITS,'This run authorizes new source scopes only; no revisit packets.'
BASELINE_FILES={b['book']:b['baseline'] for b in CONFIG['books']}
STEMS=[s for _,ss,_ in GROUPS.values() for s in ss]
FIELDS=('source_reference','target','relationship','rationale')
HISTORICAL_BINDINGS=[]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def packet_cohort(before,stem):
 scope={v['reference'] for c in before['chapters'] if c['chapter'] in PACKET_CHAPTERS[stem] for v in c['verses']}
 if stem in REVISITS:
  refs=REVISITS[stem]['source_references']
  assert refs and len(refs)==len(set(refs)) and set(refs)<=scope
  return set(refs)
 return scope

def rows(path):
 with Path(path).open(encoding='utf-8-sig',newline='') as stream:
  reader=csv.DictReader(stream,delimiter='\t')
  assert reader.fieldnames==list(FIELDS),(path,reader.fieldnames)
  result=list(reader)
 assert all(set(r)==set(FIELDS) and all(r.values()) for r in result),path
 return result

def accepted(peer):
 return (peer.get('accepted_for_integration') is True or peer.get('accepted') is True or peer.get('result')=='accepted' or isinstance(peer.get('acceptance'),dict) and peer['acceptance'].get('accepted') is True)

def any_true(receipt,names):
 return any(receipt.get(name) is True for name in names)

def source_deferrals(author):
 declared=author.get('deferred_source_units',[])
 assert isinstance(declared,list)
 refs=[d['source_reference'] for d in declared]
 assert len(set(refs))==len(refs)
 for case in declared:
  assert case.get('target') is None and case.get('reason'),case
  credit_fields=[case[k] for k in ['completed_source_credit','completed_source_verse_credit'] if k in case]
  assert credit_fields and all(v==0 for v in credit_fields) and case.get('completed_pair_credit')==0,case
  assert any_true(case,['source_unit_read','source_and_necessary_context_read','source_and_necessary_context_independently_read','source_read']),case
 # Some frozen authors repeated source-only records in legacy unresolved fields.
 # They must be exact aliases, not additional unresolved retained triples.
 for field in ['unresolved_cases','unresolved_candidates']:
  for case in author.get(field,[]):
   if case.get('target') is None:
    assert case in declared,(field,'undeclared source-only case',case)
   elif field=='unresolved_cases':
    raise AssertionError('Unresolved retained case: '+repr(case))
 return deepcopy(declared)

def target_candidates(author):
 result=[deepcopy(c) for c in author.get('unresolved_candidates',[]) if c.get('target') is not None]
 for c in result:
  assert c['completed_pair_credit']==0 and c.get('identity_resolved') is False and c.get('retained') is False,c
  assert all(c.get(k,0)==0 for k in ['completed_source_credit','completed_source_verse_credit']),c
  assert any_true(c,['source_and_target_text_read','source_and_target_read','candidate_passage_read']),c
  assert c['source_reference'] in INDEX and keys(c['target'])
 return result

def historical_local(filename,expected_sha):
 """A historical receipt may name a final TSV later replaced after review.

 Resolve only to preserved same-packet bytes having its exact declared hash.
 Current-final bindings are separately checked directly in validate_packets.
 """
 artifact=HERE/filename
 assert artifact.resolve().parent==HERE.resolve() and artifact.is_file(),filename
 if digest(artifact)==expected_sha:return artifact
 stem=next((s for s in STEMS if filename.startswith(s)),None)
 assert stem and artifact.suffix in ['.tsv','.json'],filename
 matches=sorted(p for p in HERE.glob(stem+'*'+artifact.suffix) if digest(p)==expected_sha)
 assert matches,(filename,'declared historical bytes not preserved',expected_sha)
 found=matches[0]
 binding={'declared_file':filename,'sha256':expected_sha,'preserved_snapshot':found.name}
 if binding not in HISTORICAL_BINDINGS:HISTORICAL_BINDINGS.append(binding)
 return found

def declared_local_files(value):
 """Validate explicit local filename/hash bindings in any receipt depth."""
 if isinstance(value,dict):
  for key,item in value.items():
   if isinstance(item,str) and item.endswith(('.json','.tsv')) and '/' not in item and '\\' not in item:
    expected=value.get(key+'_sha256') or value.get(key.removesuffix('_file')+'_sha256')
    if key in ('file','raw_file'):expected=expected or value.get('sha256') or value.get('raw_sha256')
    if key in ('before_file','after_file','before_tsv','after_tsv'):expected=expected or value.get(key.split('_')[0]+'_sha256')
    if key=='draft_file':expected=expected or value.get('draft_sha256')
    if key=='input_file':expected=expected or value.get('final_input_sha256') or value.get('input_sha256')
    if expected:yield historical_local(item,expected)
   elif isinstance(item,(dict,list)):yield from declared_local_files(item)
 elif isinstance(value,list):
  for item in value:yield from declared_local_files(item)

def stage_changes(stage):
 for change in stage.get('changes',stage.get('changed_triples',stage.get('exact_changed_rows',[]))):
  old=change.get('old_row',change.get('before'))
  new=change.get('new_row',change.get('after',change.get('proposed_new_row')))
  if isinstance(old,dict) or isinstance(new,dict):yield old,new

def validate_stage(path):
 stage=load(path)
 list(declared_local_files(stage))
 before=stage.get('before_file') or stage.get('before_tsv') or stage.get('draft_file') or stage.get('preserved_input_file') or stage.get('original_draft_file')
 after=stage.get('after_file') or stage.get('after_tsv') or stage.get('input_file') or stage.get('final_input_file')
 changes=list(stage_changes(stage))
 if not before and not after and not changes:return
 assert before and after,(path.name,'Incomplete explicit revision binding')
 before_hash=stage.get('before_tsv_sha256') or stage.get('before_sha256') or stage.get('draft_sha256') or stage.get('preserved_input_sha256') or stage.get('original_draft_sha256')
 after_hash=stage.get('after_tsv_sha256') or stage.get('after_sha256') or stage.get('final_input_sha256')
 assert before_hash and after_hash,path.name
 old=rows(historical_local(before,before_hash));new=rows(historical_local(after,after_hash))
 # Apply recorded exact old/new deltas by full row identity. Target changes are valid.
 expected=old.copy()
 for original,replacement in changes:
  if original is not None:
   assert original in expected,(path.name,'recorded old row absent',original)
   at=expected.index(original)
   if replacement is None:expected.pop(at)
   else:expected[at]=replacement
  else:
   assert replacement is not None and replacement not in expected
   expected.append(replacement)
 assert Counter(tuple(r[f] for f in FIELDS) for r in expected)==Counter(tuple(r[f] for f in FIELDS) for r in new),(path.name,'stage differs beyond recorded deltas')
 # Existing rows retain order; additions may be inserted into actual source order.
 added=[replacement for original,replacement in changes if original is None]
 assert [r for r in expected if r not in added]==[r for r in new if r not in added],(path.name,'undocumented retained-row reorder')
 if stage.get('receipt_precision_changes'):
  old_receipt=load(historical_local(stage['before_author_receipt'],stage['before_author_receipt_sha256']))
  stem=next(s for s in STEMS if path.name.startswith(s))
  new_receipt=load(HERE/(stem+'-review.json'))
  for change in stage['receipt_precision_changes']:
   ref=change['source_reference']
   for receipt,field in [(old_receipt,'before_reason'),(new_receipt,'after_reason')]:
    matching=[d for d in receipt['deferred_source_units'] if d['source_reference']==ref]
    assert len(matching)==1 and matching[0]['reason']==change[field],(path.name,field,ref)

def historical_archive_receipt_view(path,receipt):
 """Interpret only two byte-bound legacy attestation keys; never relax pin lists."""
 if not isinstance(receipt,dict) or 'pin_completion_file' not in receipt:return receipt
 allowed={
  'psalms-81-88-peer-review-before-attestation-field-rename.json':'0238018f7186ac32da4c7714fbed10f112ab5cc914f4abd466f9ca70f242b1cd',
  'psalms-81-88-root-peer-provisional-review.json':'56f85f93c299cd5b4d1e743607614bd487d538126b6a6885c85962a82925bc24'}
 assert path.name in allowed and digest(path)==allowed[path.name],(path.name,'Unrecognized legacy attestation field')
 correction=load(HERE/'psalms-81-88-peer-receipt-field-correction.json')
 assert (correction['run_id'],correction['base_commit'],correction['source_commit'],correction['completion_credit'])==(RUN,BASE_COMMIT,PIN,0)
 renames=[('pin_completion_file','acquisition_completion_attestation_file'),('pin_completion_sha256','acquisition_completion_attestation_sha256')]
 assert correction['renamed_fields']==[{'old_key':a,'new_key':b} for a,b in renames]
 assert {v['before_file']:v['before_sha256'] for v in correction['historical_field_views']}==allowed
 record=next(v for v in correction['historical_field_views'] if v['before_file']==path.name)
 before=checked_local(HERE,record['before_file'],record['before_sha256']);after=checked_local(HERE,record['after_file'],record['after_sha256'])
 original=before.read_bytes();assert json.loads(original)==receipt
 for old,new in renames:
  token=json.dumps(old).encode()+b':';replacement=json.dumps(new).encode()+b':'
  assert original.count(token)==1 and original.count(replacement)==0
  original=original.replace(token,replacement)
 assert original==after.read_bytes(),(path.name,'Historical interpretation changes more than two field names')
 return json.loads(original)

def archive_files(authors,peers):
 """Collect a validated transitive closure, preserving original historical bytes."""
 files=set();pending=set();visited=set();verified_leaves={};validated_lists=set()
 def add(paths):
  for path in paths:
   path=Path(path)
   assert path.resolve().parent==HERE.resolve() and path.is_file(),path
   files.add(path)
   if path not in visited:pending.add(path)
 def dependencies(receipt):
  add(declared_local_files(receipt))
  for filename,expected in declared_pin_metadata(receipt):
   metadata=checked_local(HERE,filename,expected);add([metadata])
   binding=(filename,expected)
   if binding in validated_lists:continue
   # Keep the existing strict nonempty pin-list, Git-blob and cache checks.
   add(validated_pin_artifacts(HERE,{'pin_receipt':filename,'pin_receipt_sha256':expected}))
   for pin in load(metadata):
    assert pin['commit']==PIN
    raw=checked_local(HERE,pin['raw_file'],pin['raw_sha256'])
    headers=checked_local(HERE,pin['headers_file'],pin['headers_sha256']);header=load(headers)
    assert isinstance(header,dict) and header['status']==200
    assert header['url']==f"https://raw.githubusercontent.com/{pin['repository']}/{pin['commit']}/{pin['records']}"
    for leaf,expected_hash in [(raw,pin['raw_sha256']),(headers,pin['headers_sha256'])]:
     assert leaf not in verified_leaves or verified_leaves[leaf]==expected_hash
     verified_leaves[leaf]=expected_hash
    add([headers])
   validated_lists.add(binding)
 for stem in STEMS:
  for pattern in [stem+'*.tsv',stem+'*review*.json',stem+'*refinements*.json',stem+'*refinement*.json',stem+'*correction*.json',stem+'*findings*.json',stem+'-pins.json']:
   add(HERE.glob(pattern))
  for receipt in [authors[stem],peers[stem]]:dependencies(receipt)
 while pending:
  path=min(pending);pending.remove(path)
  if path in visited:continue
  visited.add(path)
  # Verified source bodies and HTTP headers are leaves, not review receipts.
  if path in verified_leaves:
   assert digest(path)==verified_leaves[path]
   continue
  if path.suffix!='.json':continue
  receipt=historical_archive_receipt_view(path,load(path))
  dependencies(receipt)
  stem=next((s for s in STEMS if path.name.startswith(s)),None)
  if stem and 'refinement' in path.name:
   if any(k in receipt for k in ['changes','changed_triples','exact_changed_rows']):validate_stage(path)
   elif set(receipt)=={'deferred_source_units','unresolved_candidates'}:
    author=authors[stem]
    assert author.get('review_cases_file')==path.name and author.get('review_cases_sha256')==digest(path),(path.name,'Case bundle is not bound by the final author receipt')
    assert source_deferrals(receipt)==source_deferrals(author),(path.name,'Source deferrals differ from frozen author receipt')
    assert target_candidates(receipt)==target_candidates(author),(path.name,'Target candidates differ from frozen author receipt')
   elif all(k in receipt for k in ['changed_before_file','changed_before_sha256','changed_after_file','changed_after_sha256','old_complete_triples_personally_reread','corrected_complete_triples_personally_reread']):
    assert path in set(declared_local_files(authors[stem]))|set(declared_local_files(peers[stem])),(path.name,'Reading attestation is not bound by a final receipt')
    assert receipt.get('reviewer') and (receipt.get('run_id'),receipt.get('source_commit'),receipt.get('completion_credit'))==(RUN,PIN,0)
    for side,count in [('before','old_complete_triples_personally_reread'),('after','corrected_complete_triples_personally_reread')]:
     bound=historical_local(receipt['changed_'+side+'_file'],receipt['changed_'+side+'_sha256'])
     assert receipt[count]==len(rows(bound)),(path.name,'Reading attestation count differs from its exact TSV')
   else:
    assert all(k in receipt for k in ['reviewer','source_commit','final_input_sha256']),(path.name,'Unrecognized refinement document')
 assert visited==files
 return sorted(files)

def validate_packets():
 baselines={book:load(HERE/BASELINE_FILES[book]) for book in GROUPS}
 source_ranges={}
 for book,before in baselines.items():
  chapters={c for stem in GROUPS[book][1] if stem not in REVISITS for c in PACKET_CHAPTERS[stem]}
  scoped=[v for c in before['chapters'] if c['chapter'] in chapters for v in c['verses']]
  assert scoped and all(v['status']=='pending' and not v['cross_references'] for v in scoped)
  source_ranges[book]=scoped[0]['reference']+'-'+scoped[-1]['reference'].rsplit(' ',1)[-1]
  revisits=[r for s in GROUPS[book][1] if s in REVISITS for r in REVISITS[s]['source_references']]
  if revisits:source_ranges[book]+='; previously read source revisit: '+', '.join(revisits)
 packet_books={stem:book for book,(_,stems,_) in GROUPS.items() for stem in stems}
 authors={s:load(HERE/(s+'-review.json')) for s in STEMS}
 peers={s:load(HERE/(s+'-peer-review.json')) for s in STEMS}
 packets={};allrows=[];all_deferred=[];all_candidates=[];fingerprints=[];fixes=[]
 canonical={b['book'] for b in load(REPO/'canon.json')['books']}
 for stem in STEMS:
  book=packet_books[stem];before=baselines[book]
  a=authors[stem];peer=peers[stem];rr=rows(HERE/(stem+'.tsv'));h=digest(HERE/(stem+'.tsv'));ah=digest(HERE/(stem+'-review.json'))
  assert a['final_input_sha256']==h and peer.get('input_sha256',peer.get('final_input_sha256'))==h
  assert (peer.get('author_receipt_sha256') or peer.get('author_review_sha256'))==ah
  assert accepted(peer),stem+' explicit acceptance missing'
  for field in ['required_changes','required_corrections','required_removals','removals','unresolved_retained_cases','unresolved_retained_pairs']:
   assert not peer.get(field),(stem,field)
   if isinstance(peer.get('acceptance'),dict):assert not peer['acceptance'].get(field),(stem,field)
  for receipt in [a,peer]:
   assert receipt.get('run_id')==RUN and receipt.get('base_commit',receipt.get('baseline_commit'))==BASE_COMMIT,(stem,'Current run/baseline binding')
   assert receipt.get('source_book')==book,(stem,'source book differs from configured packet')
   assert receipt['source_commit']==PIN and receipt['reviewed']==DATE
   assert receipt.get('review_timezone','America/New_York')=='America/New_York'
   assert receipt.get('all_source_verses_read') is True and receipt.get('all_target_passages_read') is True
   assert any_true(receipt,['necessary_context_read','all_necessary_context_read']),(stem,'Necessary context review not declared')
   assert any_true(receipt,['all_complete_triples_independently_read','all_complete_triples_separately_reread','all_full_triples_reread'])
   for field in ['input_sha256','final_input_sha256']:
    if field in receipt:assert receipt[field]==h
  assert any_true(a,['all_retained_rationales_reread','all_rationales_reread','all_full_triples_reread'])
  assert a['source_chapters']==PACKET_CHAPTERS[stem]
  if 'source_chapters' in peer:assert peer['source_chapters']==a['source_chapters']
  cohort=packet_cohort(before,stem)
  if stem in REVISITS:
   for receipt in [a,peer]:assert receipt.get('source_references')==REVISITS[stem]['source_references'],(stem,'explicit singleton reference scope required')
   prior=load(HERE/('before-'+BOOK_CONFIG[book]['folder']+'__source-checks.json'))
   prior_deferrals=[d for d in prior.get('deferred_source_units',[]) if d['source_reference'] in cohort]
   assert {d['source_reference'] for d in prior_deferrals}==cohort and len(prior_deferrals)==len(cohort)
   assert a.get('prior_deferred_source_unit')==prior_deferrals[0] and a.get('first_reviewed_source_units')==0 and a.get('rereading_completion_credit')==0,(stem,'exact previous deferral or zero reread credit missing')
   originals={v['reference']:v for c in before['chapters'] for v in c['verses']}
   assert all(originals[r]['status']=='pending' and not originals[r]['cross_references'] for r in cohort)
  supported={r['source_reference'] for r in rr};deferred=source_deferrals(a);deferred_refs={d['source_reference'] for d in deferred}
  assert not supported & deferred_refs and supported|deferred_refs==cohort,(stem,'source partition')
  targets={k for r in rr for k in keys(r['target'])}
  for receipt in [a,peer]:
   for field in ['source_verses','completed_source_verses','reviewed_source_verses']:
    if field in receipt:assert receipt[field]==len(supported),(stem,field)
   for field in ['source_units_read','source_scope_units','source_inventory_units_in_scope']:
    if field in receipt:assert receipt[field]==len(cohort),(stem,field)
   for field in ['completed_pairs','reviewed_pairs']:
    if field in receipt:assert receipt[field]==len(rr),(stem,field)
   if 'distinct_target_verse_units' in receipt:assert receipt['distinct_target_verse_units']==len(targets)
  assert a['source_verses']==len(supported) and a['completed_pairs']==len(rr)
  overrides=a.get('pair_reviewer_overrides',[])
  assert len({(x['source_reference'],x['target']) for x in overrides})==len(overrides)
  for x in overrides:
   assert (x['source_reference'],x['target']) in {(r['source_reference'],r['target']) for r in rr}
   assert x['reviewer'] and x['reviewed']==DATE and x['review_timezone']=='America/New_York' and x['complete_corrected_triple_reread'] is True
  if 'deferred_source_count' in a:assert a['deferred_source_count']==len(deferred)
  if 'deferred_source_units' in peer:
   peer_deferred=peer['deferred_source_units']
   assert len(peer_deferred)==len(deferred_refs) and {d['source_reference'] for d in peer_deferred}==deferred_refs
   for d in peer_deferred:
    assert d.get('target') is None and d.get('completed_source_credit')==d.get('completed_pair_credit')==0
    assert any_true(d,['source_unit_read','source_and_necessary_context_read','source_and_necessary_context_independently_read','source_read'])
  for r in rr:
   assert r['source_reference'] in cohort and r['source_reference'] not in keys(r['target'])
   assert all(k in INDEX and INDEX[k]['book'] in canonical for k in keys(r['target']))
   # Substantive adequacy is established by the frozen author and independent
   # passage reviews, not an arbitrary word minimum that would demand padding.
   assert isinstance(r['rationale'],str) and r['rationale'].strip()
   assert (r['source_reference'].split(':')[0]==r['target'].split(':')[0])==('same-chapter' in r['relationship'].lower()),r
  candidates=target_candidates(a)
  if stem in REVISITS:
   assert not deferred and not candidates and supported==cohort
  for c in candidates:assert c['source_reference'] in cohort
  retained_books={INDEX[k]['book'] for k in targets}|{book}
  candidate_books={INDEX[k]['book'] for c in candidates for k in keys(c['target'])}
  for receipt,required_books in [(a,retained_books|candidate_books),(peer,retained_books|candidate_books)]:
   pin_books=set()
   for filename,expected in declared_pin_metadata(receipt):
    for pin in load(checked_local(HERE,filename,expected)):pin_books.add(pin['book'])
   assert required_books<=pin_books,(stem,'missing separately declared pin evidence',required_books-pin_books)
  packets[stem]={'book':book,'rows':rr,'cohort':cohort,'supported':supported,'deferred':deferred,'candidates':candidates,'source_units_read':len(cohort),'is_revisit':stem in REVISITS}
  allrows.extend(rr);all_deferred.extend(deferred);all_candidates.extend(candidates)
  fingerprints.append({'author_file':stem+'-review.json','author_sha256':ah,'peer_file':stem+'-peer-review.json','peer_sha256':digest(HERE/(stem+'-peer-review.json')),'tsv_file':stem+'.tsv','tsv_sha256':h})
  for key,value in a.items():
   if value and any(term in key for term in ['revision','correction','refinement']):fixes.append({'file':stem+'.tsv','field':key,'details':value,'new_pairs_credited':0})
  if isinstance(peer.get('acceptance'),dict):
   for field,expected in [('binding_tsv_sha256',h),('binding_author_receipt_sha256',ah)]:
    if field in peer['acceptance']:assert peer['acceptance'][field]==expected
 book_plans={};scope=set()
 for book,(folder,stems,_) in GROUPS.items():
  cohort=set().union(*(packets[stem]['cohort'] for stem in stems))
  assert len(cohort)==sum(len(packets[stem]['cohort']) for stem in stems),'Overlapping packet cohorts'
  revisited=set().union(*(packets[stem]['cohort'] for stem in stems if stem in REVISITS))
  newly_read=cohort-revisited
  rr=[r for stem in stems for r in packets[stem]['rows']]
  dd=[d for stem in stems for d in packets[stem]['deferred']]
  cc=[c for stem in stems for c in packets[stem]['candidates']]
  ss={r['source_reference'] for r in rr};dr={d['source_reference'] for d in dd}
  assert ss|dr==cohort and not ss & dr and len(dd)==len(dr),(book,'book source partition')
  assert not scope & cohort,(book,'overlapping source cohorts')
  scope.update(cohort)
  book_plans[book]={'folder':folder,'stems':stems,'baseline_file':BASELINE_FILES[book],'cohort':cohort,'rows':rr,'deferred':dd,'candidates':cc,'supported':ss,'source_units_read':len(cohort),'first_reviewed_source_units':len(newly_read),'revisited_source_units_read':len(revisited),'new_cohort':newly_read,'revisit_cohort':revisited,'source_range':source_ranges[book]}
 supported={r['source_reference'] for r in allrows};deferred_refs={d['source_reference'] for d in all_deferred}
 assert len(scope)==sum(p['source_units_read'] for p in book_plans.values()) and supported|deferred_refs==scope and not supported & deferred_refs
 assert len(all_deferred)==len(deferred_refs)
 assert len({(r['source_reference'],r['target']) for r in allrows})==len(allrows)
 assert len({(r['source_reference'],tuple(keys(r['target']))) for r in allrows})==len(allrows),'Repeated actual target passage under different range spelling'
 files=archive_files(authors,peers)
 return {'authors':authors,'peers':peers,'packets':packets,'books':book_plans,'rows':allrows,'deferred':all_deferred,'candidates':all_candidates,'fingerprints':fingerprints,'fixes':fixes,'files':files,'supported':supported,'source_units_read':len(scope),'first_reviewed_source_units':sum(p['first_reviewed_source_units'] for p in book_plans.values()),'revisited_source_units_read':sum(p['revisited_source_units_read'] for p in book_plans.values()),'source_range':'; '.join(source_ranges.values()),'historical_filename_bindings':deepcopy(HISTORICAL_BINDINGS)}
