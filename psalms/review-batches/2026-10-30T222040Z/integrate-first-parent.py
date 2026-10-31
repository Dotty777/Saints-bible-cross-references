"""Prepare the final unread Psalms units and new Proverbs source prefix; all checks precede writes.

--preflight-only prepares and validates all outputs without repository mutations.
Only root may execute this helper after completing the semantic review gates.
"""
from pathlib import Path
from copy import deepcopy
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,os,re,runpy,subprocess,sys,uuid
from passages import INDEX,keys,complete_text
from complete_evidence_contract import evidence_unit,text_sha,verify_complete_edge
from review_contract import HERE,REPO,RUN,DATE,PIN,BASE_COMMIT as REVIEW_BASE_COMMIT,GROUPS,STEMS,BOOK_CONFIG,CONFIG,REVISITS,load,digest,validate_packets
from publication_parent import PUBLICATION_PARENT,publication_contract,require_parent_ready,validate_output_scope
BASE_COMMIT=PUBLICATION_PARENT  # Only the transaction/checkout parent; review_contract keeps the review base.
from pin_artifact_contract import declared_pin_metadata
from run_support import run_support,PRODUCTION_PATHS,validate_target_headers
assert set(sys.argv[1:]) <= {"--apply","--preflight-only"}, "Unknown integration option"
assert not ({"--apply","--preflight-only"} <= set(sys.argv[1:])), "Choose apply or preflight"

def encoded(x):return (json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
def slug(x):return re.sub('[^a-z0-9]+','-',x.lower()).strip('-')
def require(ok,msg):assert ok,msg
def flat(x):return [v for c in x['chapters'] for v in c['verses']]
def gsha(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=REPO)
publication=publication_contract();assert publication['review_base']==REVIEW_BASE_COMMIT
baseline=load(HERE/'before-progress.json');progress=load(REPO/'progress.json')
assert progress==load(HERE/'publication-parent-progress.json') and progress['next']['reference']=='1 Chronicles 1:24' and progress['next_unreviewed']['reference']=='Psalms 118:1'
concurrent_working_copy_before=require_parent_ready(publication)
assert len(baseline['runs'])==37 and not any(r.get('run_id')==RUN for r in baseline['runs'])
assert (baseline['completed_source_verses'],baseline['completed_cross_references'],baseline['completed_chapters'],baseline['completed_book_records'],baseline['pending_book_records'])==(16129,20852,420,12,31)
baseline_files={path:'before-'+path.replace('/','__') for path in load(HERE/'baseline-metadata.json')['files']}
meta=load(HERE/'baseline-metadata.json');assert meta['commit']==REVIEW_BASE_COMMIT and set(meta['files'])==set(baseline_files)
assert set(meta['files'])=={'canon.json','progress.json','psalms/verses.json','psalms/source-checks.json','psalms/inventory.json','psalms/editorial-notes.json','psalms/verification.json'}
for path,saved in baseline_files.items():
 raw=git('show',REVIEW_BASE_COMMIT+':'+path)
 assert gsha(raw)==meta['files'][path] and json.loads(raw)==load(HERE/saved),path
 assert json.loads(git('show',BASE_COMMIT+':'+path))==load(REPO/path),path
before_files={p.relative_to(REPO).as_posix():digest(p) for p in REPO.rglob('*') if p.is_file() and '.git' not in p.relative_to(REPO).parts}
plan=validate_packets()
assert list(GROUPS)==['Psalms','Proverbs'] and BOOK_CONFIG['Psalms']['new'] is False and BOOK_CONFIG['Proverbs']['new'] is True
assert (plan['first_reviewed_source_units'],plan['revisited_source_units_read'],plan['source_units_read'])==(632,0,632)
assert not REVISITS and all(not b['revisit_cohort'] for b in plan['books'].values())
hint_contract=runpy.run_path(str(HERE/'audit-common.py'))
hintgroups=hint_contract['unavailable_hint_groups'](plan['authors'],plan['packets'])
hintcount=sum(len(g['hints']) for g in hintgroups)
continuation_folders=[b['records'].rstrip('/') for b in baseline['books'] if b['status']!='completed' and b.get('total_source_verse_units') is not None and b['book'] not in GROUPS]
assert continuation_folders==['1-chronicles','2-chronicles','1-maccabees','2-maccabees','ezra','nehemiah','esther','job']
assert load(HERE/'receipt-fingerprints.json')==plan['fingerprints'] and load(HERE/'applied-corrections.json')==plan['fixes']
preflight=load(HERE/'target-identity-preflight.json')
assert preflight['source_units_read']==plan['source_units_read'] and preflight['source_units']==len(plan['supported']) and preflight['retained_pairs']==len(plan['rows'])
assert preflight['unavailable_target_locator_hint_count']==hintcount and preflight['unavailable_locator_hints_are_unread'] is True and preflight['unavailable_locator_hint_completion_credit']==0
manifest=load(HERE.parent/'source-manifest.json')
registry={b['book']:{'path':b['records'],'blob_sha':b.get('blob_sha') or b['sha']} for b in manifest['books']}
paths={b['records']+'verses.json':b['book'] for b in load(HERE.parent/'reference/progress.json')['books'] if b.get('records')}
canonical={b['book'] for b in load(REPO/'canon.json')['books']}
allchecks={}
for b in baseline['books']:
 path=REPO/b['records']/'source-checks.json'
 if path.is_file():
  allchecks[b['book']]=load(path)
  for s in allchecks[b['book']]['sources']:
   assert s['commit']==PIN
   book=paths[s['path']];value={'path':s['path'],'blob_sha':s['blob_sha']}
   if book in registry:assert registry[book]==value
   registry[book]=value
assert len(allchecks)==21
assert sum(len(c.get('unresolved_candidates',[])) for c in allchecks.values())==285
assert sum(len(c.get('deferred_source_units',[])) for c in allchecks.values())==1313
# Target-only provenance adds no source inventory or review credit.
targetextras=load(HERE/'extra-target-sources.json');ezrafiles=[HERE/'extra-target-sources.json']
for extra in targetextras:
 raw=(HERE/extra['raw_file']).read_bytes();metadata=load(HERE/extra['metadata_file'])
 assert extra['book'] in canonical and extra['book'] not in registry and extra['commit']==PIN and extra['completion_credit']==0
 assert metadata['repository']==manifest['repository'] and metadata['ref']==PIN and metadata['path']==extra['path']
 assert metadata['sha']==extra['blob_sha']==gsha(raw) and hashlib.sha256(raw).hexdigest()==extra['raw_sha256'] and digest(HERE/extra['metadata_file'])==extra['metadata_sha256']
 assert json.loads(raw)==load(HERE.parent/'reference'/(extra['path'].split('/')[0]+'.json')) and json.loads(raw)['book']==extra['book']
 assert validate_target_headers(extra)
 registry[extra['book']]={'path':extra['path'],'blob_sha':extra['blob_sha']};ezrafiles.extend([HERE/extra['raw_file'],HERE/extra['metadata_file'],HERE/extra['headers_file']])
for receipt in list(plan['authors'].values())+list(plan['peers'].values()):
 for filename,expected in declared_pin_metadata(receipt):
  for pin in load(HERE/filename):
   value={'path':pin['records'],'blob_sha':pin['blob_sha']}
   assert registry[pin['book']]==value,(pin['book'],'pin registry mismatch')
def source(book):
 value=registry[book]
 return {'repository':manifest['repository'],'commit':PIN,**value,'url':f'https://github.com/{manifest["repository"]}/blob/{PIN}/{value["path"]}'}

support=run_support();newfolders=support['newfolders'];inventories=support['inventories'];inventory_files=support['files'];inventory_evidence=support['inventory_evidence']
chapter_units=support['chapter_units'];completed_chapter_numbers=support['completed_chapter_numbers'];completed_source_sections=support['completed_source_sections']
states={};inputs=[];all_new_deferred=[];all_new_candidates=[];results=[]
for book,(folder,stems,total_chapters) in GROUPS.items():
 bp=plan['books'][book];before=load(HERE/bp['baseline_file']);data=deepcopy(before);total_chapters=len(chapter_units(before));total_sections=len(before['chapters'])
 checks=deepcopy(allchecks[book]) if book in allchecks else load(newfolders[book]/'source-checks.json')
 notes=load(REPO/folder/'editorial-notes.json') if book in allchecks else load(newfolders[book]/'editorial-notes.json')
 checks.setdefault('deferred_source_units',[]);checks.setdefault('unresolved_candidates',[])
 old_done={v['reference'] for v in flat(before) if v['status']=='completed'}
 old_pair_count=sum(len(v['cross_references']) for v in flat(before));old_deferrals=deepcopy(checks['deferred_source_units']);old_candidates=deepcopy(checks['unresolved_candidates'])
 assert (len(old_done),old_pair_count,len(old_deferrals),len(old_candidates))=={'Psalms':(1733,1826,289,79),'Proverbs':(0,0,0,0)}[book]
 resolved=[]
 retained_old_deferrals=deepcopy(old_deferrals)
 assert not bp['revisit_cohort'] and len(retained_old_deferrals)==len(old_deferrals)
 checks['deferred_source_units']=deepcopy(retained_old_deferrals)
 assert checks.get('resolved_source_deferrals',[])==allchecks.get(book,{}).get('resolved_source_deferrals',[])
 units={v['reference']:v for v in flat(data)}
 assert len(units)==before['total_source_verse_units'] and len(data['chapters'])==total_sections
 book_inputs=[];paircounts=Counter();rowcount=0
 for stem in stems:
  a=plan['authors'][stem];packet=plan['packets'][stem]
  item={'file':stem+'.tsv','sha256':digest(HERE/(stem+'.tsv')),'pairs':len(packet['rows']),'source_units_read':packet['source_units_read'],'supported_source_units':len(packet['supported']),'deferred_source_units':len(packet['deferred'])}
  inputs.append(item);book_inputs.append(item)
  for row in packet['rows']:
   ref=row['source_reference'];unit=units[ref]
   assert ref not in old_done and ref in bp['supported']
   assert unit['text']==INDEX[ref]['text'] and unit['id']==INDEX[ref]['id']
   kk=keys(row['target']);evidence=[evidence_unit(k) for k in kk]
   assert len({INDEX[k]['book'] for k in kk})==1
   edge={'id':slug(ref)+'__'+slug(row['target']),'target':row['target'],'verdict':'supported','relationship':row['relationship'],'rationale':row['rationale'],'reviewed':a['reviewed'],'reviewer':a['reviewer'],'review_batch':RUN,'source_text_sha256':text_sha(unit['text']),'target_source':source(INDEX[kk[0]]['book']),'target_verses':evidence,'target_passage_sha256':text_sha('\n'.join(v['reference']+' '+v['text'] for v in evidence)),'destination_anchor_check':'not performed; reference resolves to saved source records'}
   if unit.get('continuation_paragraphs'):edge['source_complete_text_sha256']=text_sha(complete_text(unit))
   overrides=[x for x in a.get('pair_reviewer_overrides',[]) if x['source_reference']==ref and x['target']==row['target']]
   assert len(overrides)<=1
   if overrides:edge['reviewer']=overrides[0]['reviewer']
   if any(v.get('continuation_paragraphs') for v in evidence):edge['target_passage_complete_sha256']=text_sha('\n'.join(v['reference']+' '+complete_text(v) for v in evidence))
   verify_complete_edge(unit,edge,require)
   assert not any(tuple(keys(e['target']))==tuple(kk) for e in unit['cross_references'])
   unit['cross_references'].append(edge);unit['status']='completed';unit['reviewed']=a['reviewed']
   paircounts[str(ref.rsplit(' ',1)[-1].split(':')[0])]+=1;rowcount+=1
 new_deferred=[];new_candidates=[]
 for stem in stems:
  a=plan['authors'][stem]
  for original in plan['packets'][stem]['deferred']:
   d=deepcopy(original);ref=d['source_reference']
   assert ref not in old_done|bp['supported'] and units[ref]['status']=='pending' and not units[ref]['cross_references']
   d.update(source_snapshot=deepcopy(data['source_snapshot']),source_verse=evidence_unit(ref),reviewer=a['reviewer'],reviewed=a['reviewed'],review_timezone='America/New_York',review_batch=RUN,source_unit_read=True,completed_source_credit=0,completed_pair_credit=0)
   new_deferred.append(d)
  for original in plan['packets'][stem]['candidates']:
   d=deepcopy(original);kk=keys(d['target'])
   d.update(source_snapshot=deepcopy(data['source_snapshot']),source_verse=evidence_unit(d['source_reference']),target_source=source(INDEX[kk[0]]['book']),target_verses=[evidence_unit(k) for k in kk],reviewer=a['reviewer'],reviewed=a['reviewed'],review_timezone='America/New_York',review_batch=RUN)
   assert d['completed_pair_credit']==0 and d['identity_resolved'] is False
   new_candidates.append(d)
 for c,oc in zip(data['chapters'],before['chapters']):
  assert {k:v for k,v in c.items() if k not in ['status','verses']}=={k:v for k,v in oc.items() if k not in ['status','verses']}
  assert len(c['verses'])==len(oc['verses'])
  for v,ov in zip(c['verses'],oc['verses']):
   if ov['reference'] not in bp['supported']:assert v==ov,ov['reference']+' historical or pending object changed'
   else:
    assert ov['status']=='pending' and not ov['cross_references']
    assert {k:x for k,x in v.items() if k not in ['status','cross_references','reviewed']}=={k:x for k,x in ov.items() if k not in ['status','cross_references','reviewed']}
  c['status']='completed' if all(v['status']=='completed' for v in c['verses']) else 'pending'
 allunits=flat(data);done=[v for v in allunits if v['status']=='completed'];edges=[e for v in done for e in v['cross_references']];pending=[v for v in allunits if v['status']!='completed']
 assert {v['reference'] for v in done}==old_done|bp['supported'] and len(edges)==old_pair_count+len(bp['rows']) and rowcount==len(bp['rows'])
 checks['deferred_source_units'].extend(new_deferred);checks['unresolved_candidates'].extend(new_candidates)
 assert checks['deferred_source_units'][:len(retained_old_deferrals)]==retained_old_deferrals and checks['unresolved_candidates'][:len(old_candidates)]==old_candidates
 deferredrefs={d['source_reference'] for d in checks['deferred_source_units']}
 assert len(deferredrefs)==len(checks['deferred_source_units']) and deferredrefs<={v['reference'] for v in pending}
 readrefs=old_done|{d['source_reference'] for d in old_deferrals}|bp['cohort']
 unread=[v for v in allunits if v['reference'] not in readrefs]
 assert {v['reference'] for v in pending}==deferredrefs|{v['reference'] for v in unread}
 first_pending=pending[0] if pending else None;first_unread=unread[0] if unread else None
 ordered_before=flat(before);previous_read=old_done|{d['source_reference'] for d in old_deferrals}
 never_read=[v['reference'] for v in ordered_before if v['reference'] not in previous_read]
 assert bp['new_cohort']==set(never_read[:bp['first_reviewed_source_units']]),'New review must be the next exact source-order prefix'
 if book!=list(GROUPS)[-1]:assert not unread,'Later book cannot start before preceding source units were read'
 completed_numbers=completed_chapter_numbers(data);old_completed_numbers=completed_chapter_numbers(before)
 newchapters=[number for number in completed_numbers if number not in old_completed_numbers]
 next_ref=first_pending['reference'] if first_pending else None;next_unread=first_unread['reference'] if first_unread else None
 data.update(date=DATE,completed_source_verses=len(done),completed_cross_references=len(edges),completed_chapters=completed_numbers,next_reference=next_ref,next_unreviewed_reference=next_unread,review_status=('initial_curated_pass_complete' if not pending else 'initial_source_reading_complete_with_pending_evidence') if not unread else 'initial_curated_pass_in_progress')
 if 'total_source_sections' in data:data['completed_source_sections']=completed_source_sections(data)
 checked_passage=allunits[0]['reference']+'-'+allunits[len(readrefs)-1]['reference'].rsplit(' ',1)[-1]
 checks.update(date=DATE,method='Complete actual source and retained target passages with necessary context were read and every retained explanation separately reread in the recorded batches. Unsupported source units remain pending with zero completion credit. Earlier completed objects and all unresolved evidence are preserved. No earlier source-only deferral or unresolved candidate is resolved or removed in this run. Inventory alone earns no review credit. No exhaustive discovery or independent specialist verification is claimed.',checked_scope={'source_passage':checked_passage,'source_passage_is_review_scope':True,'source_units_read':len(readrefs),'source_verse_units':len(done),'deferred_source_units':len(deferredrefs),'retained_pairs':len(edges),'distinct_target_verse_units':len({v['reference'] for e in edges for v in e['target_verses']})},next_unreviewed_reference=next_unread)
 used={book}|{INDEX[t['reference']]['book'] for e in edges for t in e['target_verses']}|{INDEX[k]['book'] for c in checks['unresolved_candidates'] for k in keys(c['target'])}
 checks['sources']=[source(b) for b in sorted(used)]
 checks['pending']=['First pending source unit: '+(next_ref or 'none'),f'{len(readrefs)} of {len(allunits)} original source units have been read; {len(unread)} are never reviewed. Deferred source units remain incomplete.','Next never-reviewed source: __GLOBAL_NEXT__.','Read but deferred source units: '+(', '.join(d['source_reference'] for d in checks['deferred_source_units']) or 'none'),'Independent specialist review','Live destination anchors and reader display checks']+['Target evidence pending: '+c['source_reference']+' / '+c['target'] for c in checks['unresolved_candidates']]
 checks['review_batches'].append({'run_id':RUN,'records':'review-batches/'+RUN+'.json','new_source_verses':len(bp['supported']),'new_pairs':len(bp['rows']),'source_units_read':bp['source_units_read'],'first_reviewed_source_units':bp['first_reviewed_source_units'],'revisited_source_units_read':bp['revisited_source_units_read'],'resolved_source_deferrals':len(resolved),'deferred_source_units':len(new_deferred),'unresolved_retained_cases':0})
 notes['date']=DATE
 for stem in stems:
  for note in plan['authors'][stem].get('editorial_notes',[]):
   if note not in notes['notes']:notes['notes'].append(note)
 note=hint_contract['unavailable_hint_note']([g for g in hintgroups if g['packet'] in stems])
 if note and note not in notes['notes']:notes['notes'].append(note)
 record=next(b for b in progress['books'] if b['book']==book)
 if BOOK_CONFIG[book]['new']:
  assert record.get('total_source_verse_units') is None
  record.update(inventory_status='complete for pinned source',total_source_verse_units=len(allunits),total_chapters=total_chapters)
 if 'total_source_sections' in data:record.update(total_source_sections=data['total_source_sections'],completed_source_sections=data['completed_source_sections'])
 record.update(status='completed' if not pending else 'in_progress',completed_source_verses=len(done),completed_cross_references=len(edges),completed_chapters=data['completed_chapters'],next_reference=next_ref,next_unreviewed_reference=next_unread,completed_verse_ranges=[c['verses'][0]['reference']+'-'+c['verses'][-1]['reference'].rsplit(':',1)[-1] for c in data['chapters'] if c['status']=='completed'])
 result={'book':book,'source_range':bp['source_range'],'source_range_is_review_scope':True,'source_units_read':bp['source_units_read'],'first_reviewed_source_units':bp['first_reviewed_source_units'],'revisited_source_units_read':bp['revisited_source_units_read'],'new_completed_revisited_sources':len(resolved),'distinct_source_verses':len(bp['supported']),'new_completed_pairs':len(bp['rows']),'new_deferred_source_units_count':len(new_deferred),'total_deferred_source_units_count':len(deferredrefs),'completed_chapters':data['completed_chapters'],'new_completed_chapters':newchapters,'reviewed_dates':[DATE],'book_initial_curated_pass_complete':not pending,'all_original_source_units_read':not unread,'next_reference':next_ref,'next_unreviewed_reference':next_unread}
 results.append(result);all_new_deferred.extend(new_deferred);all_new_candidates.extend(new_candidates)
 states[book]={'folder':folder,'data':data,'checks':checks,'notes':notes,'done':done,'edges':edges,'pending':pending,'unread':unread,'new_deferred':new_deferred,'new_candidates':new_candidates,'newchapters':newchapters,'result':result,'paircounts':dict(paircounts),'inputs':book_inputs,'resolved_source_deferrals':resolved}

lastbook=list(states)[-1];nextpending=deepcopy(baseline['next'])
assert lastbook=='Proverbs' and not states['Psalms']['unread'] and states[lastbook]['unread'] and states[lastbook]['unread'][0]['reference']=='Proverbs 5:1'
nextconfig=CONFIG['next_new_review'];assert nextconfig=={'book':'Proverbs','chapter':5,'reference':'Proverbs 5:1','inventory_required_before_source_review':False}
nextrecord=next(b for b in progress['books'] if b['book']==nextconfig['book'])
assert nextrecord['order']==22 and nextrecord['total_source_verse_units']==939 and nextrecord['total_chapters']==31 and nextrecord['total_source_sections']==34
nextnew={k:nextconfig[k] for k in ['book','chapter','reference']};nextnew['source_id']=INDEX[nextnew['reference']]['id']
orders=[next(b['order'] for b in progress['books'] if b['book']==book) for book in states]
assert orders==list(range(orders[0],orders[-1]+1)) and list(states)[0]==baseline['next_unreviewed']['book']
for state in states.values():state['checks']['pending']=[p.replace('__GLOBAL_NEXT__',nextnew['reference']) for p in state['checks']['pending']]
progress.update(updated=DATE,updated_at_utc=datetime.now(timezone.utc).isoformat(),completed_source_verses=sum(b['completed_source_verses'] for b in progress['books']),completed_cross_references=sum(b['completed_cross_references'] for b in progress['books']),completed_chapters=sum(len(b.get('completed_chapters',[])) for b in progress['books']),completed_book_records=sum(b['status']=='completed' for b in progress['books']),pending_book_records=sum(b['status']!='completed' for b in progress['books']),next=nextpending,next_unreviewed=nextnew)
for old,new in zip(baseline['books'],progress['books']):
 if old['book'] not in GROUPS:assert old==new
assert sum(b.get('total_source_verse_units') is None for b in progress['books'])==21 and len(inventories)==1
known=[];known_deferred=[]
for b in progress['books']:
 checks=states[b['book']]['checks'] if b['book'] in states else allchecks.get(b['book'])
 if checks:
  known.extend(checks.get('unresolved_candidates',[]));known_deferred.extend(checks.get('deferred_source_units',[]))
assert len(known)==285+len(all_new_candidates) and len(known_deferred)==1313+len(all_new_deferred)
newchaptercount=sum(len(s['newchapters']) for s in states.values())
assert progress['completed_source_verses']==16129+len(plan['supported']) and progress['completed_cross_references']==20852+len(plan['rows']) and progress['completed_chapters']==420+newchaptercount
run={'run_id':RUN,'date':DATE,'synchronized':DATE,'reviewed_dates':[DATE],'source_range':plan['source_range'],'source_range_is_review_scope':True,'source_units_read':plan['source_units_read'],'first_reviewed_source_units':plan['first_reviewed_source_units'],'revisited_source_units_read':plan['revisited_source_units_read'],'new_completed_revisited_sources':0,'resolved_source_deferrals_count':0,'distinct_source_verses':len(plan['supported']),'new_completed_pairs':len(plan['rows']),'new_deferred_source_units_count':len(all_new_deferred),'total_deferred_source_units_count':len(known_deferred),'book_results':results,'hourly_target':500,'target_met':len(plan['rows'])>=500,'target_shortfall':max(0,500-len(plan['rows'])),'target_excess':max(0,len(plan['rows'])-500),'unresolved_retained_cases':0,'new_unresolved_candidate_count':len(all_new_candidates),'known_pending_target_candidate_count':len(known),'review_record':'review-batches/'+RUN+'.json','next_reference':nextpending['reference'],'next_unreviewed_reference':nextnew['reference'],'inventories_added':inventories}
run.update(review_base_commit=REVIEW_BASE_COMMIT,publication_parent=BASE_COMMIT,publication_parent_reconciliation_file='publication-parent-reconciliation.json',publication_parent_reconciliation_sha256=digest(HERE/'publication-parent-reconciliation.json'),preserved_nt_tree_git_sha=publication['preserved_nt_tree_git_sha'])
progress['runs'].append(run);assert progress['runs'][:-1]==baseline['runs'] and len(progress['runs'])==38
archivefiles=sorted(set(plan['files']+inventory_files+ezrafiles));archive_relative='psalms/review-batches/'+RUN+'/'
batch={**run,'source_repository':manifest['repository'],'source_commit':PIN,'reviewed':DATE,'completion_definition':states['Psalms']['data']['completion_definition'],'inputs':inputs,'chapter_pair_counts':{book:s['paircounts'] for book,s in states.items()},'review_receipts':list(plan['authors'].values()),'peer_review_receipts':list(plan['peers'].values()),'applied_peer_corrections':plan['fixes'],'resolved_source_deferrals':[d for st in states.values() for d in st['resolved_source_deferrals']],'first_review_scope':'Psalms 118:1 through Psalms 151:7, then Proverbs 1:1 through Proverbs 4:27b; 632 first-reviewed units','revisit_scope':[],'next_new_review_inventory_required':False,'deferred_source_units':all_new_deferred,'known_pending_source_units':known_deferred,'unresolved_candidates':all_new_candidates,'known_pending_target_candidates':known,'excluded_candidates':[c for a in plan['authors'].values() for c in a.get('candidate_exclusions',[])],'unresolved_retained_cases':[],'remaining_checks':['Deferred source units require substantive supported review','Next never-reviewed source: '+nextnew['reference'],'Independent human specialist review','Original-language and critical-apparatus comparison','Live destination-anchor and display verification'],'target_identity_preflight':preflight,'frozen_receipt_fingerprints':plan['fingerprints'],'input_archive':archive_relative,'archived_input_files':[{'file':p.name,'sha256':digest(p),'completion_credit':0} for p in archivefiles],'inventory_evidence':inventory_evidence,'target_provenance_added':targetextras,'historical_filename_bindings':plan['historical_filename_bindings'],'continuation_only_updates':[{'book':book,'new_review_credit':0,'first_pending':ref,'next_new_source_review':nextnew['reference']} for book,ref in [(b['book'],b['next_reference']) for b in baseline['books'] if b['book'] in allchecks and b['book'] not in GROUPS and b['status']!='completed']]}
assert len({p.name for p in archivefiles})==len(archivefiles),'Flat archive name collision'
batch.update(technical_support_archive=support['archive_manifest'],prepared_production_change_contract=support['contract'])
batch.update(unavailable_locator_hints_by_packet=hintgroups,unavailable_target_locator_hint_count=hintcount,unavailable_locator_hints_are_unread=True,unavailable_locator_hint_completion_credit=0)
assert {HERE/g['author_receipt_file'] for g in hintgroups}|{HERE/p['file'] for g in hintgroups for p in g['availability_records']} <= set(archivefiles)
outputs=dict(support['production_outputs'])
for book,newfolder in newfolders.items():
 for p in newfolder.iterdir():
  assert p.is_file();outputs[BOOK_CONFIG[book]['folder']+'/'+p.name]=p.read_bytes()
for book,s in states.items():
 folder=s['folder'];stems=plan['books'][book]['stems']
 local_batch={**batch,**s['result'],'book_results':[s['result']],'inputs':s['inputs'],'chapter_pair_counts':{book:s['paircounts']},'review_receipts':[plan['authors'][stem] for stem in stems],'peer_review_receipts':[plan['peers'][stem] for stem in stems],'applied_peer_corrections':[c for c in plan['fixes'] if c['file'] in {stem+'.tsv' for stem in stems}],'deferred_source_units':s['new_deferred'],'known_pending_source_units':s['checks']['deferred_source_units'],'unresolved_candidates':s['new_candidates'],'known_pending_target_candidates':s['checks']['unresolved_candidates'],'new_unresolved_candidate_count':len(s['new_candidates']),'known_pending_target_candidate_count':len(s['checks']['unresolved_candidates']),'excluded_candidates':[c for stem in stems for c in plan['authors'][stem].get('candidate_exclusions',[])],'overall_distinct_source_verses':len(plan['supported']),'overall_new_completed_pairs':len(plan['rows']),'overall_source_units_read':plan['source_units_read'],'overall_reviewed_dates':[DATE],'overall_review_record':'../../review-batches/'+RUN+'.json','overall_next_unreviewed_reference':nextnew['reference'],'hourly_target_scope':'The hourly target, target_met, target_shortfall and target_excess cover this entire ordered run and are evaluated against overall_new_completed_pairs. This local record credits only its own book in distinct_source_verses and new_completed_pairs. Pending evidence, source rereading and new-book inventory earn zero credit.'}
 local_hintgroups=[g for g in hintgroups if g['packet'] in stems]
 local_batch.update(unavailable_locator_hints_by_packet=local_hintgroups,unavailable_target_locator_hint_count=sum(len(g['hints']) for g in local_hintgroups))
 restore_path=REPO/folder/'RESTORE.md' if book in allchecks else newfolders[book]/'RESTORE.md'
 restore=restore_path.read_text(encoding='utf-8');marker='\n## Pending source review recovery\n'
 if marker in restore:restore=restore[:restore.index(marker)]
 recovery=f'{len(flat(s["data"]))} original {book} source units in {len(chapter_units(s["data"]))} native chapters and {len(s["data"]["chapters"])} original source sections were inventoried before review. {len(s["done"])+len(s["checks"]["deferred_source_units"])} units have been read: {len(s["done"])} completed source units and {len(s["edges"])} retained pairs; {len(s["unread"])} units are never reviewed. Read but deferred sources earn zero completion credit: '+(', '.join(d['source_reference'] for d in s['checks']['deferred_source_units']) or 'none')+'. First unfinished source: **'+(s['result']['next_reference'] or 'none')+'**. Next never-reviewed source in this book: **'+(s['result']['next_unreviewed_reference'] or 'none')+'**. Keep this book incomplete while any source unit remains pending. Earlier source deferrals and unresolved candidates remain unchanged; this run reviews only the next never-reviewed source units.'
 restore=restore.rstrip()+'\n\n## Pending source review recovery\n\n'+recovery+'\n\nThe next new source review is **'+nextnew['reference']+'**. Root progress.json keeps its earliest-pending next at **'+nextpending['reference']+'** and its separate next_unreviewed at **'+nextnew['reference']+'**. Recompute both positions from actual ordered source objects after every update. Preserve earlier completed objects, source fields, anchors, continuation bodies, pending cases and review batches. Inventory, unresolved evidence and rereading add no completion credit. The complete Psalms inventory remains unchanged at 2534 original units in 151 chapters. The new Proverbs inventory preserves 939 original units in 31 native chapters and 34 source sections; a native chapter completes only after all of its source sections complete.\n'
 outputs.update({folder+'/verses.json':encoded(s['data']),folder+'/source-checks.json':encoded(s['checks']),folder+'/editorial-notes.json':encoded(s['notes']),folder+'/RESTORE.md':restore.encode(),folder+'/review-batches/'+RUN+'.json':encoded(local_batch)})
oldnew=baseline['next_unreviewed']['reference']
def update_continuation(value):
 for prefix,suffix in [('Next new source review: ','.'),('Next never-reviewed source: ','.'),('The next new source review is **','**'),('separate next_unreviewed at **','**')]:
  value=value.replace(prefix+oldnew+suffix,prefix+nextnew['reference']+suffix)
 return value
outputs.update({'progress.json':encoded(progress),'review-batches/'+RUN+'.json':encoded(batch)})
for folder in continuation_folders:
 checks=deepcopy(load(HERE/('before-'+folder+'__source-checks.json')))
 checks['pending']=[update_continuation(s) for s in checks['pending']]
 restore=update_continuation((REPO/folder/'RESTORE.md').read_text(encoding='utf-8'))
 outputs.update({folder+'/source-checks.json':encoded(checks),folder+'/RESTORE.md':restore.encode()})
for p in archivefiles:outputs[archive_relative+p.name]=p.read_bytes()
for item in batch['archived_input_files']:assert hashlib.sha256(outputs[archive_relative+item['file']]).hexdigest()==item['sha256']
attributes='# Preserve exact frozen evidence and raw source bytes.\n* -text whitespace=cr-at-eol\n'
for p in archivefiles:
 if p.read_bytes().replace(b'\r\n',b'\n').endswith(b'\n\n'):attributes+=p.name+' whitespace=cr-at-eol,-blank-at-eof\n'
outputs[archive_relative+'.gitattributes']=attributes.encode()
allowed_existing={'progress.json'}|{folder+'/'+name for folder in continuation_folders for name in ['source-checks.json','RESTORE.md']}|{config['folder']+'/'+name for config in BOOK_CONFIG.values() if not config['new'] for name in ['verses.json','source-checks.json','editorial-notes.json','RESTORE.md']}
allowed_existing|={f['path'] for f in support['contract']['files'] if f['before_sha256'] is not None}
assert all(path in allowed_existing or path not in before_files for path in outputs)
assert {path for path in outputs if path.startswith('scripts/')}==PRODUCTION_PATHS
assert {path for path in outputs if path.endswith('/inventory.json')}=={'proverbs/inventory.json'} and 'canon.json' not in outputs
assert all(hashlib.sha256(outputs[f['path']]).hexdigest()==f['after_sha256'] for f in support['contract']['files'])
validate_output_scope(outputs,publication)
assert all(digest(REPO/path)==sha for path,sha in before_files.items())
assert not (REPO/archive_relative).exists()
summary={'run':run,'completed_source_verses':progress['completed_source_verses'],'completed_pairs':progress['completed_cross_references'],'completed_chapters':progress['completed_chapters'],'next':progress['next'],'next_unreviewed':nextnew,'book_totals':{book:{'completed_sources':len(s['done']),'completed_pairs':len(s['edges']),'pending_sources':len(s['pending']),'deferred_sources':len(s['checks']['deferred_source_units']),'unreviewed_sources':len(s['unread'])} for book,s in states.items()},'archive_files':len(archivefiles),'repository_output_files':len(outputs)}
summary.update(review_base_commit=REVIEW_BASE_COMMIT,publication_parent=BASE_COMMIT,concurrent_working_copy_before=concurrent_working_copy_before)
if '--apply' not in sys.argv or '--preflight-only' in sys.argv:print(json.dumps({'preflight_only':True,**summary}));raise SystemExit(0)
# Stage complete outputs and exact old bytes outside the repository first.
# The journal survives interruption, including interruption between replacement
# and the following journal update: recovery compares actual old/new bytes.
transaction_id=RUN+'-'+uuid.uuid4().hex
transaction=HERE/('integration-transaction-'+transaction_id)
transaction.mkdir();(transaction/'outputs').mkdir();(transaction/'originals').mkdir()
repo_root=REPO.resolve();journal_path=transaction/'recovery-manifest.json'
created_temporaries=set();replaced_paths=set()
journal={'schema_version':1,'run_id':RUN,'baseline_commit':BASE_COMMIT,'repository':str(repo_root),'state':'preparing','completion_credit':0,'entries':[],'created_directories':[],'rollback_conflicts':[],'journal_errors':[],'recovery_rule':'For each entry, preserve any current bytes differing from both original and staged bytes. Restore original bytes only if the current file still equals staged bytes; remove a newly created file only if it still equals staged bytes. Temporary files may be removed only when their bytes are an exact prefix of their declared staged/original artifact. Remove only recorded, empty created directories; never recursively delete. Recheck resolved paths within repository before each mutation.'}
def checked_path(relative):
 path=REPO/relative
 assert path.resolve().is_relative_to(repo_root) and path.resolve()!=repo_root,'Path outside repository: '+relative
 assert not path.is_symlink(),'Symlink output path: '+relative
 parent=path.parent
 while parent!=REPO:
  assert not parent.is_symlink(),'Symlink output parent: '+str(parent)
  parent=parent.parent
 return path
def current_bytes(path):
 if path.exists():
  assert path.is_file() and not path.is_symlink(),'Output is not a regular file: '+str(path)
  return path.read_bytes()
 return None
def durable_write(path,raw):
 with path.open('wb') as stream:
  stream.write(raw);stream.flush();os.fsync(stream.fileno())
def save_journal():
 temporary=transaction/'recovery-manifest.next.json'
 durable_write(temporary,encoded(journal));os.replace(temporary,journal_path)
def try_save_journal():
 try:save_journal()
 except BaseException as error:journal['journal_errors'].append(repr(error))
for i,(relative,raw) in enumerate(outputs.items()):
 path=checked_path(relative);original=current_bytes(path)
 if relative in before_files:assert original is not None and hashlib.sha256(original).hexdigest()==before_files[relative],relative+' changed before staging'
 else:assert original is None,relative+' appeared before staging'
 staged='outputs/'+str(i)+'.bin';backup='originals/'+str(i)+'.bin' if original is not None else None
 durable_write(transaction/staged,raw)
 if original is not None:durable_write(transaction/backup,original)
 assert (transaction/staged).read_bytes()==raw and (backup is None or (transaction/backup).read_bytes()==original)
 temporary=path.parent/('.codex-'+transaction_id+'-'+str(i)+'.tmp')
 restore_temporary=path.parent/('.codex-'+transaction_id+'-'+str(i)+'.restore.tmp')
 assert not temporary.exists() and not restore_temporary.exists()
 journal['entries'].append({'path':relative,'original_exists':original is not None,'original_file':backup,'original_sha256':hashlib.sha256(original).hexdigest() if original is not None else None,'staged_file':staged,'staged_sha256':hashlib.sha256(raw).hexdigest(),'temporary_path':temporary.relative_to(REPO).as_posix(),'restore_temporary_path':restore_temporary.relative_to(REPO).as_posix(),'state':'prepared'})
journal['state']='prepared';save_journal()
# Last full-baseline check. Scratch staging has not touched repository files.
assert git('rev-parse','HEAD').decode().strip()==BASE_COMMIT and not git('status','--porcelain').strip()
assert all(digest(REPO/path)==value for path,value in before_files.items())
for entry in journal['entries']:
 expected=(transaction/entry['original_file']).read_bytes() if entry['original_exists'] else None
 assert current_bytes(checked_path(entry['path']))==expected,entry['path']+' changed before write boundary'
def ensure_parent(path):
 missing=[];parent=path.parent
 while parent!=REPO and not parent.exists():missing.append(parent);parent=parent.parent
 for directory in reversed(missing):
  relative=directory.relative_to(REPO).as_posix();checked_path(relative)
  # Write-ahead directory intent supports recovery if interrupted after mkdir.
  journal.setdefault('directory_intents',[]).append(relative);save_journal()
  directory.mkdir();journal['created_directories'].append(relative);save_journal()
def atomic_replace(relative,raw,expected,temporary_relative):
 path=checked_path(relative);temporary=checked_path(temporary_relative)
 assert current_bytes(path)==expected,relative+' changed concurrently'
 # Exclusive creation prevents overwriting any existing temporary path.
 fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0))
 created_temporaries.add(temporary_relative)
 try:
  offset=0
  while offset<len(raw):
   written=os.write(fd,raw[offset:]);assert written>0,'Short write';offset+=written
  os.fsync(fd)
 finally:os.close(fd)
 assert temporary.read_bytes()==raw,'Staged temporary bytes differ'
 checked_path(relative);checked_path(temporary_relative)
 assert current_bytes(path)==expected,relative+' changed during temporary write'
 os.replace(temporary,path)
 replaced_paths.add(relative)

# WRITE BOUNDARY: originals, final bytes and the durable journal are complete.
try:
 journal['state']='applying';save_journal()
 for entry in journal['entries']:
  original=(transaction/entry['original_file']).read_bytes() if entry['original_exists'] else None
  final=(transaction/entry['staged_file']).read_bytes()
  assert hashlib.sha256(final).hexdigest()==entry['staged_sha256']
  if original is not None:assert hashlib.sha256(original).hexdigest()==entry['original_sha256']
  path=checked_path(entry['path']);assert current_bytes(path)==original,entry['path']+' changed concurrently'
  ensure_parent(path)
  entry['state']='replacing';save_journal()
  atomic_replace(entry['path'],final,original,entry['temporary_path'])
  entry['state']='applied';save_journal()
 journal['state']='applied';save_journal()
except BaseException as error:
 journal['failure']=repr(error);journal['state']='rolling_back';try_save_journal()
 for entry in reversed(journal['entries']):
  try:
   original=(transaction/entry['original_file']).read_bytes() if entry['original_exists'] else None
   final=(transaction/entry['staged_file']).read_bytes();path=checked_path(entry['path']);current=current_bytes(path)
   assert hashlib.sha256(final).hexdigest()==entry['staged_sha256']
   if original is not None:assert hashlib.sha256(original).hexdigest()==entry['original_sha256']
   if current!=original:
    assert entry['path'] in replaced_paths,entry['path']+' was not replaced by this process; preserved'
    assert current==final,entry['path']+' has concurrent or unexpected bytes; preserved'
    if original is None:
     assert current_bytes(checked_path(entry['path']))==final;path.unlink()
    else:atomic_replace(entry['path'],original,final,entry['restore_temporary_path'])
   entry['state']='rolled_back'
  except BaseException as rollback_error:journal['rollback_conflicts'].append({'path':entry['path'],'error':repr(rollback_error)})
  # An interrupted write can leave a known prefix in an exclusively created
  # temporary file. Anything else is preserved for manual recovery.
  for field,artifact in [('temporary_path',entry['staged_file']),('restore_temporary_path',entry['original_file'])]:
   try:
    if entry[field] not in created_temporaries:continue
    temporary=checked_path(entry[field]);raw=current_bytes(temporary)
    if raw is not None:
     expected=(transaction/artifact).read_bytes() if artifact else None
     assert expected is not None and raw==expected[:len(raw)],entry[field]+' has unexpected bytes; preserved'
     assert current_bytes(checked_path(entry[field]))==raw;temporary.unlink()
   except BaseException as temporary_error:journal['rollback_conflicts'].append({'path':entry[field],'error':repr(temporary_error)})
  try_save_journal()
 for relative in reversed(journal['created_directories']):
  try:
   directory=checked_path(relative)
   if directory.exists():directory.rmdir()  # Empty directories only.
  except BaseException as directory_error:journal['rollback_conflicts'].append({'path':relative,'error':repr(directory_error)})
 journal['state']='rollback_requires_attention' if journal['rollback_conflicts'] else 'rolled_back';try_save_journal()
 raise RuntimeError('Integration failed; guarded rollback attempted. Recovery journal: '+str(journal_path)) from error
(HERE/'merge-result.json').write_bytes(encoded(summary));print(json.dumps(summary))
