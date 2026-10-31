"""Read-only audit of complete evidence, preservation, credit and publication.

This helper writes only its scratch audit report. It never renders, alters source
records or calls the validator with receipt writing enabled.
"""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
from collections import Counter
import argparse,html,importlib.util,json,re,runpy,sys
globals().update({k:v for k,v in runpy.run_path(str(Path(__file__).resolve().parent/'audit-common.py')).items() if not k.startswith('__')})
from review_contract import validate_packets,STEMS,GROUPS,BOOK_CONFIG
from complete_evidence_contract import evidence_unit,verify_complete_edge
from passages import INDEX,keys,complete_text
from pin_artifact_contract import declared_pin_metadata
ap=argparse.ArgumentParser();ap.add_argument('--require-staged',action='store_true');ap.add_argument('--published',action='store_true');opt=ap.parse_args()
before=load(H/'before-progress.json');p=load(R/'progress.json');batch=load(R/f'review-batches/{RUN}.json');run=p['runs'][-1]
require(before==old('progress.json') and len(before['runs'])==36 and p['runs'][:-1]==before['runs'] and len(p['runs'])==37 and run['run_id']==RUN,'Historical run objects changed')
require(load(R/'canon.json')==old('canon.json')==load(H/'before-canon.json'),'Canon changed')
metadata=load(H/'baseline-metadata.json');require(metadata['commit']==BASE,'Baseline commit differs')
saved={path:'before-'+path.replace('/','__') for path in metadata['files']}
require(set(metadata['files'])==set(saved),'Baseline metadata coverage differs')
for path,name in saved.items():
 raw=git('show',BASE+':'+path);require(gsha(raw)==metadata['files'][path] and json.loads(raw)==load(H/name),'Fresh baseline object differs: '+path)
oldtree={line.split('\t',1)[1]:line.split('\t',1)[0].split()[2] for line in git('ls-tree','-r',BASE).decode().splitlines()}
index={line.split('\t',1)[1]:line.split('\t',1)[0].split()[1] for line in git('ls-files','--stage').decode().splitlines()}
changed=set(git('diff','--name-only',BASE).decode().splitlines());untracked=set(git('ls-files','--others','--exclude-standard').decode().splitlines())
generated={f+'/'+name for f in OLD_FOLDERS for name in ['README.md','verification.json',old(f+'/verses.json')['readable_html'],old(f+'/verses.json')['readable_text']]}
allowed={'README.md','progress.json'}|{folder+'/'+name for folder in CONTINUATION_FOLDERS for name in ['source-checks.json','RESTORE.md']}|{'psalms/'+name for name in ['verses.json','source-checks.json','editorial-notes.json','RESTORE.md']}|generated
# Every production script is immutable in this run.
immutable={path:blob for path,blob in oldtree.items() if path not in allowed}
require(not set(immutable)&changed and all((R/path).is_file() for path in immutable),'Old records, inventories, archives or production code changed')
if opt.require_staged or opt.published:
 require(not git('diff','--name-only').strip() and not untracked,'Unstaged/untracked files remain')
 require(all(index.get(path)==blob for path,blob in immutable.items()),'Immutable staged Git object changed')
for f in PRIOR:
 for name in ['verses.json','source-checks.json']+(['inventory.json'] if (R/f/'inventory.json').exists() else []):require(load(R/f/name)==old(f+'/'+name),'Prior completed-book record changed')
 for name in ['README.md',old(f+'/verses.json')['readable_html'],old(f+'/verses.json')['readable_text']]:require((R/f/name).read_text(encoding='utf-8-sig')==git('show',BASE+':'+f+'/'+name).decode('utf-8-sig').replace('\r\n','\n'),'Prior readable changed')
 a=old(f+'/verification.json');b=load(R/f/'verification.json');require({k:v for k,v in a.items() if k!='checked_at_utc'}=={k:v for k,v in b.items() if k!='checked_at_utc'},'Prior verification changed beyond timestamp')
oldnext=before['next_unreviewed']['reference'];newnext=p['next_unreviewed']['reference']
require(oldnext=='Psalms 81:1' and newnext=='Psalms 118:1','Unexpected review cursor')
def update_continuation_labels(value):
 for prefix,suffix in [('Next new source review: ','.'),('Next never-reviewed source: ','.'),('The next new source review is **','**'),('separate next_unreviewed at **','**')]:
  value=value.replace(prefix+oldnext+suffix,prefix+newnext+suffix)
 return value
for folder,count,deferred in [(f,old(f+'/verses.json')['completed_source_verses'],len(old(f+'/source-checks.json').get('deferred_source_units',[]))) for f in CONTINUATION_FOLDERS]:
 graph=load(R/folder/'verses.json');checks=load(R/folder/'source-checks.json');priorchecks=old(folder+'/source-checks.json')
 require(graph==old(folder+'/verses.json')==load(H/('before-'+folder+'__verses.json')) and graph['completed_source_verses']==count,folder+' graph changed')
 require(len(checks['deferred_source_units'])==deferred and {k:v for k,v in checks.items() if k!='pending'}=={k:v for k,v in priorchecks.items() if k!='pending'} and checks['pending']==[update_continuation_labels(v) for v in priorchecks['pending']],folder+' checks changed beyond continuation')
 a=old(folder+'/verification.json');b=load(R/folder/'verification.json')
 require({k:v for k,v in a.items() if k!='checked_at_utc'}=={k:v for k,v in b.items() if k!='checked_at_utc'},folder+' technical verification changed beyond timestamp')
 for name in ['RESTORE.md','README.md',graph['readable_html'],graph['readable_text']]:
  require((R/folder/name).read_text(encoding='utf-8-sig')==update_continuation_labels(git('show',BASE+':'+folder+'/'+name).decode('utf-8-sig').replace('\r\n','\n')),folder+' readable/recovery changed beyond continuation: '+name)
plan=validate_packets();require((plan['first_reviewed_source_units'],plan['revisited_source_units_read'],plan['source_units_read'])==(672,0,672),'First-reading/revisit partition differs');authors=[plan['authors'][s] for s in STEMS];peers=[plan['peers'][s] for s in STEMS]
hintgroups=unavailable_hint_groups(plan['authors'],plan['packets']);hintcount=sum(len(g['hints']) for g in hintgroups)
require(batch['unavailable_locator_hints_by_packet']==hintgroups and batch['unavailable_target_locator_hint_count']==hintcount and batch['unavailable_locator_hints_are_unread'] is True and batch['unavailable_locator_hint_completion_credit']==0,'Unavailable unread locator preservation differs')
require(run['date']==run['synchronized']==p['updated']==DATE,'Review dates differ')
require(batch['review_receipts']==authors and batch['peer_review_receipts']==peers,'Frozen review receipts differ')
require(batch['frozen_receipt_fingerprints']==plan['fingerprints']==load(H/'receipt-fingerprints.json') and batch['applied_peer_corrections']==plan['fixes']==load(H/'applied-corrections.json'),'Final fingerprint/corrections differ')
require(batch['target_identity_preflight']==load(H/'target-identity-preflight.json'),'Target preflight differs')
require(batch['historical_filename_bindings']==plan['historical_filename_bindings'],'Historical binding differs')
pins=[]
for receipt in authors+peers:
 for filename,expected in declared_pin_metadata(receipt):
  require(sha((H/filename).read_bytes())==expected,'Declared pin metadata SHA differs')
  for pin in load(H/filename):
   raw=(H/pin['raw_file']).read_bytes();require(gsha(raw)==pin['blob_sha'] and sha(raw)==pin['raw_sha256'] and json.loads(raw)==load(H.parent/'reference'/(pin['records'].split('/')[0]+'.json')),'Complete pinned source differs');pins.append(pin)
pinmap={v['records']:v['blob_sha'] for v in pins}
require(all(pinmap[v['records']]==v['blob_sha'] for v in pins),'Conflicting pinned source identity')
pinbookmap={v['book']:{'path':v['records'],'blob_sha':v['blob_sha']} for v in pins}
def expected_target_source(reference):
 value=pinbookmap[INDEX[reference]['book']]
 return {'repository':'Dotty777/Saints-Translation','commit':PIN,**value,'url':f'https://github.com/Dotty777/Saints-Translation/blob/{PIN}/{value["path"]}'}
inventory_records={};inventoryfiles=[];inventory_summaries=[]
require(not any(c['new'] for c in BOOK_CONFIG.values()),'Unexpected new inventory')
require(batch['inventory_evidence']==[v['evidence'] for v in inventory_records.values()] and run['inventories_added']==inventory_summaries,'Inventory receipt binding differs')
targetextras=load(H/'extra-target-sources.json');targetfiles=[H/'extra-target-sources.json']
require(batch['target_provenance_added']==targetextras,'New target provenance receipt differs')
for extra in targetextras:
 raw=(H/extra['raw_file']).read_bytes();meta=load(H/extra['metadata_file'])
 require(extra['commit']==PIN and extra['completion_credit']==0 and extra['book'] in {b['book'] for b in load(R/'canon.json')['books']} and meta['ref']==PIN and meta['path']==extra['path'],'Target-only provenance scope differs')
 require(gsha(raw)==extra['blob_sha']==meta['sha'] and (extra['path'] not in pinmap or pinmap[extra['path']]==extra['blob_sha']) and sha(raw)==extra['raw_sha256'] and sha((H/extra['metadata_file']).read_bytes())==extra['metadata_sha256'],'New target byte identity differs')
 require(json.loads(raw)==load(H.parent/'reference'/(extra['path'].split('/')[0]+'.json')) and not (R/extra['path'].split('/')[0]).exists(),'Target-only cache or source-review boundary differs')
 headers=load(H/extra['headers_file'])
 require(sha((H/extra['headers_file']).read_bytes())==extra['headers_sha256'] and headers['status']==200 and headers['url']==f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/'+extra['path'],'Target HTTP headers differ')
 require(datetime.fromisoformat(headers['retrieved_at_utc'])>=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc),'Target fetch predates this run')
 targetfiles.extend([H/extra['raw_file'],H/extra['metadata_file'],H/extra['headers_file']])
states={};allnewdef=[];allnewcases=[];results=[];newchaptercount=0
for book,(folder,stems,total_chapters) in GROUPS.items():
 bp=plan['books'][book];d=load(R/folder/'verses.json');checks=load(R/folder/'source-checks.json');local=load(R/folder/f'review-batches/{RUN}.json');before_d=load(H/bp['baseline_file'])
 before_checks=old(folder+'/source-checks.json') if not BOOK_CONFIG[book]['new'] else load(H/('new-'+folder)/'source-checks.json')
 total_chapters=len(before_d['chapters'])
 rawsource=load(H/next(x['raw_file'] for x in pins if x['records']==folder+'/verses.json'))
 require(d['source_snapshot']==before_d['source_snapshot']==checks['source_snapshot'] and d['source_snapshot']['commit']==PIN and pinmap[folder+'/verses.json']==d['source_snapshot']['blob_sha'],'Source snapshot differs')
 require(d['source_metadata']['original_book_metadata']=={k:v for k,v in rawsource.items() if k!='chapters'},'Original book metadata differs')
 inv=load(R/folder/'inventory.json');require(inv==(old(folder+'/inventory.json') if not BOOK_CONFIG[book]['new'] else inventory_records[book]['inventory']),'Full inventory differs')
 require(len(flat(d))==before_d['total_source_verse_units'] and len(d['chapters'])==total_chapters,'Inventory size differs')
 require([(v['reference'],v['id'],sha(v['text'].encode())) for v in flat(d)]==[(v['reference'],v['id'],v['text_sha256']) for c in inv['chapters'] for v in c['units']],'Original ordered references, anchors or text hashes differ')
 mapping={(r['source_reference'],r['target']):r for r in bp['rows']};old_done={v['reference'] for v in flat(before_d) if v['status']=='completed'};oldpairs=sum(len(v['cross_references']) for v in flat(before_d))
 require((len(old_done),oldpairs)==(1115,1171),'Prior source/pair counts differ')
 reviewers={}
 for stem in stems:
  a=plan['authors'][stem]
  for row in plan['packets'][stem]['rows']:reviewers[(row['source_reference'],row['target'])]=a['reviewer']
  for x in a.get('pair_reviewer_overrides',[]):reviewers[(x['source_reference'],x['target'])]=x['reviewer']
 require(len(rawsource['chapters'])==len(d['chapters'])==len(before_d['chapters']),'Chapter count changed')
 for srcch,ch,oldch in zip(rawsource['chapters'],d['chapters'],before_d['chapters']):
  require(ch['source_metadata']=={k:v for k,v in srcch.items() if k!='verses'},'Original chapter metadata differs')
  require({k:v for k,v in ch.items() if k not in ['status','verses']}=={k:v for k,v in oldch.items() if k not in ['status','verses']},'Tracker chapter metadata changed')
  require(len(srcch['verses'])==len(ch['verses'])==len(oldch['verses']),'Original unit counts changed')
  for src,v,ov in zip(srcch['verses'],ch['verses'],oldch['verses']):
   for k,x in src.items():require((v['source_metadata'][k] if k=='status' else v[k])==x,'Original source field changed: '+v['reference']+' '+k)
   if v['reference'] not in bp['supported']:require(v==ov,'Prior completed or pending unit changed: '+v['reference'])
   else:
    require(ov['status']=='pending' and not ov['cross_references'] and v['status']=='completed' and v['reviewed']==DATE,'New source state differs')
    require({k:x for k,x in v.items() if k not in ['status','cross_references','reviewed']}=={k:x for k,x in ov.items() if k not in ['status','cross_references','reviewed']},'New source original fields changed')
    require(len({tuple(keys(e['target'])) for e in v['cross_references']})==len(v['cross_references']),'Duplicate actual target passage')
    for e in v['cross_references']:
     row=mapping.pop((v['reference'],e['target']));require(e['rationale']==row['rationale'] and e['relationship']==row['relationship'] and e['reviewed']==DATE and e['review_batch']==RUN and e['verdict']=='supported','Frozen new pair differs');verify_complete_edge(v,e,require)
     require(e['reviewer']==reviewers[(v['reference'],e['target'])],'Actual pair reviewer attribution differs')
     require(e['target_source'] in checks['sources'] and e['target_source']==expected_target_source(keys(e['target'])[0]),'Target provenance differs')
  require(ch['status']==('completed' if all(v['status']=='completed' for v in ch['verses']) else 'pending'),'Chapter status differs')
 require(not mapping,'New retained pairs missing')
 olddef=before_checks.get('deferred_source_units',[]);oldcases=before_checks.get('unresolved_candidates',[])
 retained_olddef=[x for x in olddef if x['source_reference'] not in bp['revisit_cohort']]
 require((len(olddef),len(oldcases),len(retained_olddef))==(235,48,235),'Old Psalms pending counts differ')
 expected_resolved=[]
 require(not bp['revisit_cohort'] and all(not plan['packets'][s]['is_revisit'] for s in stems),'Unexpected revisit')
 require(checks.get('resolved_source_deferrals',[])==before_checks.get('resolved_source_deferrals',[]) and batch['resolved_source_deferrals']==local['resolved_source_deferrals']==[],'Prior resolved history changed or new resolution fabricated')
 require(checks['unresolved_candidates'][:len(oldcases)]==oldcases and checks['deferred_source_units'][:len(retained_olddef)]==retained_olddef and checks['review_batches'][:-1]==before_checks['review_batches'],'Prior pending/history objects changed')
 ds=checks['deferred_source_units'][len(retained_olddef):];cs=checks['unresolved_candidates'][len(oldcases):]
 require(len(ds)==len(bp['deferred']) and len(cs)==len(bp['candidates']),'New pending counts differ')
 for original,saved in zip(bp['deferred'],ds):
  require(all(saved[k]==v for k,v in original.items()) and saved.get('target') is None and saved['completed_source_credit']==saved['completed_pair_credit']==0,'Source deferral lost or credited')
  require(saved['source_verse']==evidence_unit(saved['source_reference']) and saved['source_snapshot']==d['source_snapshot'] and saved['review_batch']==RUN and saved['source_unit_read'] is True,'Source deferral evidence differs')
 for original,saved in zip(bp['candidates'],cs):
  require(all(saved[k]==v for k,v in original.items()) and saved['completed_pair_credit']==0 and saved['identity_resolved'] is False,'Pending target proposal lost or credited')
  require(saved['source_verse']==evidence_unit(saved['source_reference']) and saved['target_verses']==[evidence_unit(k) for k in keys(saved['target'])] and saved['target_source']==expected_target_source(keys(saved['target'])[0]),'Pending target exact evidence differs')
 done=[v for v in flat(d) if v['status']=='completed'];edges=[e for v in done for e in v['cross_references']];pending=[v for v in flat(d) if v['status']!='completed'];readrefs=old_done|{c['source_reference'] for c in olddef}|bp['cohort'];unread=[v for v in flat(d) if v['reference'] not in readrefs]
 require(len(done)==len(old_done)+len(bp['supported']) and len(edges)==oldpairs+len(bp['rows']),'Actual source/pair credit differs')
 require(len(readrefs)+len(unread)==len(flat(d)) and not readrefs&{v['reference'] for v in unread},'Actual read partition differs')
 previous_read=old_done|{c['source_reference'] for c in olddef};never_read=[v['reference'] for v in flat(before_d) if v['reference'] not in previous_read]
 require(bp['new_cohort']==set(never_read[:bp['first_reviewed_source_units']]),'Review did not follow the exact next source-order prefix')
 require(len({c['source_reference'] for c in checks['deferred_source_units']})==len(checks['deferred_source_units']) and {v['reference'] for v in pending}=={c['source_reference'] for c in checks['deferred_source_units']}|{v['reference'] for v in unread},'Pending source partition differs')
 nextref=pending[0]['reference'] if pending else None;nextunread=unread[0]['reference'] if unread else None
 require(d['next_reference']==nextref and d['next_unreviewed_reference']==checks['next_unreviewed_reference']==nextunread,'Book continuation differs')
 if book!=list(GROUPS)[-1]:require(not unread,'Earlier book still contains never-reviewed sources')
 else:require(nextunread==newnext=='Psalms 118:1','Existing Psalms continuation differs')
 completed=[c['chapter'] for c in d['chapters'] if c['status']=='completed'];newchap=[c for c in completed if c not in before_d['completed_chapters']];newchaptercount+=len(newchap)
 require(d['completed_source_verses']==len(done) and d['completed_cross_references']==len(edges) and d['completed_chapters']==completed,'Book totals differ')
 expected_scope={'source_passage':flat(d)[0]['reference']+'-'+flat(d)[len(readrefs)-1]['reference'].rsplit(' ',1)[-1],'source_passage_is_review_scope':True,'source_units_read':len(readrefs),'source_verse_units':len(done),'deferred_source_units':len(checks['deferred_source_units']),'retained_pairs':len(edges),'distinct_target_verse_units':len({t['reference'] for e in edges for t in e['target_verses']})}
 require(checks['checked_scope']==expected_scope and checks['inventory_evidence']==before_checks['inventory_evidence'],'Checked scope or inventory evidence differs')
 expected_result={'book':book,'source_range':bp['source_range'],'source_range_is_review_scope':True,'source_units_read':bp['source_units_read'],'first_reviewed_source_units':bp['first_reviewed_source_units'],'revisited_source_units_read':bp['revisited_source_units_read'],'new_completed_revisited_sources':len(expected_resolved),'distinct_source_verses':len(bp['supported']),'new_completed_pairs':len(bp['rows']),'new_deferred_source_units_count':len(ds),'total_deferred_source_units_count':len(checks['deferred_source_units']),'completed_chapters':completed,'new_completed_chapters':newchap,'reviewed_dates':[DATE],'book_initial_curated_pass_complete':not pending,'all_original_source_units_read':not unread,'next_reference':nextref,'next_unreviewed_reference':nextunread}
 results.append(expected_result)
 require(local['book_results']==[expected_result] and all(local[k]==v for k,v in expected_result.items()),'Book result/credit differs')
 require(local['known_pending_target_candidates']==checks['unresolved_candidates'] and local['known_pending_source_units']==checks['deferred_source_units'] and local['deferred_source_units']==ds and local['unresolved_candidates']==cs,'Local pending evidence crossed book boundary')
 require(local['review_receipts']==[plan['authors'][s] for s in stems] and local['peer_review_receipts']==[plan['peers'][s] for s in stems],'Local receipts crossed book boundary')
 require(local['new_unresolved_candidate_count']==len(cs) and local['known_pending_target_candidate_count']==len(checks['unresolved_candidates']),'Local candidate count differs')
 require(local['overall_distinct_source_verses']==len(plan['supported']) and local['overall_new_completed_pairs']==len(plan['rows']) and local['overall_source_units_read']==plan['source_units_read'] and local['overall_next_unreviewed_reference']==newnext,'Local overall credit/cursor differs')
 require(local['chapter_pair_counts']=={book:dict(Counter(r['source_reference'].rsplit(' ',1)[-1].split(':')[0] for r in bp['rows']))},'Chapter pair totals differ')
 require(local['inputs']==[{'file':s+'.tsv','sha256':sha((H/(s+'.tsv')).read_bytes()),'pairs':len(plan['packets'][s]['rows']),'source_units_read':plan['packets'][s]['source_units_read'],'supported_source_units':len(plan['packets'][s]['supported']),'deferred_source_units':len(plan['packets'][s]['deferred'])} for s in stems],'Local input credit differs')
 require(checks['review_batches'][-1]=={'run_id':RUN,'records':'review-batches/'+RUN+'.json','new_source_verses':len(bp['supported']),'new_pairs':len(bp['rows']),'source_units_read':bp['source_units_read'],'first_reviewed_source_units':bp['first_reviewed_source_units'],'revisited_source_units_read':bp['revisited_source_units_read'],'resolved_source_deferrals':len(expected_resolved),'deferred_source_units':len(ds),'unresolved_retained_cases':0},'Book batch summary differs')
 record=next(b for b in p['books'] if b['book']==book)
 require(record['status']==('completed' if not pending else 'in_progress') and record['completed_source_verses']==len(done) and record['completed_cross_references']==len(edges) and record['completed_chapters']==completed and record['next_reference']==nextref and record['next_unreviewed_reference']==nextunread,'Book progress differs')
 notes=load(R/folder/'editorial-notes.json');oldnotes=old(folder+'/editorial-notes.json') if not BOOK_CONFIG[book]['new'] else load(H/('new-'+folder)/'editorial-notes.json')
 require(notes['notes'][:len(oldnotes['notes'])]==oldnotes['notes'],'Prior editorial notes changed')
 expected_notes=list(oldnotes['notes'])
 for stem in stems:
  for note in plan['authors'][stem].get('editorial_notes',[]):
   if note not in expected_notes:expected_notes.append(note)
 note=unavailable_hint_note([g for g in hintgroups if g['packet'] in stems])
 if note and note not in expected_notes:expected_notes.append(note)
 require(notes=={**oldnotes,'date':DATE,'notes':expected_notes},'Editorial changes exceed current receipts')
 require(local['unavailable_locator_hints_by_packet']==hintgroups and local['unavailable_target_locator_hint_count']==hintcount and local['unavailable_locator_hints_are_unread'] is True and local['unavailable_locator_hint_completion_credit']==0,'Local unavailable hint preservation differs')
 text=(R/folder/d['readable_text']).read_text(encoding='utf-8');page=(R/folder/d['readable_html']).read_text(encoding='utf-8')
 for row in bp['rows']:require(row['target']+' — '+row['relationship']+': '+row['rationale'] in text and html.escape(row['rationale']) in page,'Readable pair differs')
 for unit in done:
  require(complete_text(unit) in text and html.escape(complete_text(unit)) in page,'Complete source body missing from readable')
  for edge in unit['cross_references']:
   for target in edge['target_verses']:require(html.escape(complete_text(target)) in page,'Complete target body missing from readable')
 restore=(R/folder/'RESTORE.md').read_text(encoding='utf-8');require('**1 Chronicles 1:24**' in restore and '**'+newnext+'**' in restore and '**'+(nextref or 'none')+'**' in restore,'Recovery cursor absent')
 for c in checks['deferred_source_units']:require(c['source_reference'] in restore,'Recovery pending source absent')
 states[book]={'data':d,'checks':checks,'local':local,'done':done,'edges':edges,'pending':pending,'unread':unread,'new_deferred':ds,'new_candidates':cs};allnewdef.extend(ds);allnewcases.extend(cs)

knowncases=[c for f in FOLDERS for c in load(R/f/'source-checks.json').get('unresolved_candidates',[])];knowndef=[c for f in FOLDERS for c in load(R/f/'source-checks.json').get('deferred_source_units',[])]
require(len(knowncases)==254+len(allnewcases) and len(knowndef)==1259+len(allnewdef),'Global pending counts differ')
require(batch['known_pending_target_candidates']==knowncases and batch['known_pending_source_units']==knowndef and batch['unresolved_candidates']==allnewcases and batch['deferred_source_units']==allnewdef,'Root pending evidence differs')
require(run['book_results']==batch['book_results']==results,'Root book results differ')
require(run['distinct_source_verses']==len(plan['supported']) and run['new_completed_pairs']==len(plan['rows']) and run['source_units_read']==plan['source_units_read'] and len(plan['supported'])+len(allnewdef)==plan['source_units_read'],'New source/pair/read credit differs')
require(run['first_reviewed_source_units']==672 and run['revisited_source_units_read']==run['new_completed_revisited_sources']==run['resolved_source_deferrals_count']==0 and batch['revisit_scope']==[] and batch['next_new_review_inventory_required'] is False,'Continuation or zero-revisit accounting differs')
require(run['new_unresolved_candidate_count']==len(allnewcases) and run['known_pending_target_candidate_count']==len(knowncases) and run['new_deferred_source_units_count']==len(allnewdef) and run['total_deferred_source_units_count']==len(knowndef),'Run pending counts differ')
require(all(batch[k]==v for k,v in run.items() if k!='unresolved_retained_cases'),'Root batch/run fields differ')
require(batch['unresolved_retained_cases']==[] and run['unresolved_retained_cases']==0,'Unresolved retained pair credited')
for entry in [run]+[s['local'] for s in states.values()]:require(entry['target_met']==(len(plan['rows'])>=500) and entry['target_shortfall']==max(0,500-len(plan['rows'])) and entry['target_excess']==max(0,len(plan['rows'])-500),'Hourly credit differs')
require((p['completed_source_verses'],p['completed_cross_references'],p['completed_chapters'],p['completed_book_records'],p['pending_book_records'])==(15511+len(plan['supported']),20197+len(plan['rows']),406+newchaptercount,sum(b['status']=='completed' for b in p['books']),sum(b['status']!='completed' for b in p['books'])),'Cumulative credit differs')
for field in ['completed_source_verses','completed_cross_references']:require(p[field]==sum(b[field] for b in p['books']),'Book sum differs')
require(p['completed_chapters']==sum(len(b.get('completed_chapters',[])) for b in p['books']) and sum(b.get('total_source_verse_units') is None for b in p['books'])==22 and not inventory_records,'Chapter or unknown inventory counts differ')
require(all(a==b for a,b in zip(before['books'],p['books']) if a['book'] not in GROUPS) and len(p['books'])==43,'Other book progress changed')
require([next(b['order'] for b in p['books'] if b['book']==book) for book in GROUPS]==[21],'Canonical source order differs')
require(p['next']==before['next'] and p['next']['reference']==run['next_reference']=='1 Chronicles 1:24' and run['next_unreviewed_reference']==newnext and p['next_unreviewed']=={'book':'Psalms','chapter':118,'reference':newnext,'source_id':INDEX[newnext]['id']},'Global cursors differ')
files=sorted(set(plan['files']+inventoryfiles+targetfiles))
require({H/g['author_receipt_file'] for g in hintgroups}|{H/p['file'] for g in hintgroups for p in g['availability_records']} <= set(files),'Unavailable evidence missing from archive plan')
require(batch['input_archive']==f'psalms/review-batches/{RUN}/','Shared archive location differs')
archive=R/batch['input_archive'];require(archive.resolve().is_relative_to(R.resolve()) and '* -text' in (archive/'.gitattributes').read_text(),'Archive byte protection absent')
require({x['file'] for x in batch['archived_input_files']}=={q.name for q in files} and {q.name for q in archive.iterdir()}=={q.name for q in files}|{'.gitattributes'},'Archive coverage differs')
for item in batch['archived_input_files']:
 q=archive/item['file'];raw=q.read_bytes();require(raw==(H/item['file']).read_bytes() and sha(raw)==item['sha256'] and item['completion_credit']==0,'Frozen archive bytes differ')
 if opt.require_staged or opt.published:require(index[q.relative_to(R).as_posix()]==gsha(raw) and git('show',':'+q.relative_to(R).as_posix())==raw,'Staged evidence bytes differ')
for s in states.values():require(s['local']['input_archive']==batch['input_archive'] and s['local']['archived_input_files']==batch['archived_input_files'],'Local archive binding differs')
newbookfiles={b['folder']+'/'+q.name for b in BOOK_CONFIG.values() if b['new'] for q in (H/('new-'+b['folder'])).iterdir()}|{b['folder']+'/'+q for book,b in BOOK_CONFIG.items() if b['new'] for q in ['verification.json',states[book]['data']['readable_html'],states[book]['data']['readable_text']]}
allowednew={f'review-batches/{RUN}.json'}|{b['folder']+f'/review-batches/{RUN}.json' for b in BOOK_CONFIG.values()}|{q.relative_to(R).as_posix() for q in archive.iterdir()}|newbookfiles
require(changed|untracked <= allowed|allowednew,'Unexpected changed/new files: '+repr(sorted((changed|untracked)-(allowed|allowednew))))
for f in CONTINUATION_FOLDERS+[b['folder'] for b in BOOK_CONFIG.values()]:
 data=load(R/f/'verses.json')
 for name in ['README.md',data['readable_html'],data['readable_text']]:require(newnext in (R/f/name).read_text(encoding='utf-8'),'Readable continuation absent')
root=(R/'README.md').read_text(encoding='utf-8');require('**Next: 1 Chronicles 1:24.**' in root and '**Next new source review: '+newnext+'.**' in root,'README cursors absent')
spec=importlib.util.spec_from_file_location('current_validator',R/'scripts/validate.py');validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator);reports=validator.validate(write_receipts=False)
remote=[];fresh=[]
if opt.published:
 meta=load(H/'published-metadata.json');commit=meta['commit'];require(set(meta['files'])==required_paths(),'Fresh MCP readback coverage differs')
 require(git('rev-parse','HEAD').decode().strip()==git('rev-parse','origin/main').decode().strip()==git('ls-remote','origin','refs/heads/main').decode().split()[0]==commit and not git('status','--porcelain').strip(),'Published main differs or dirty')
 require(git('merge-base','--is-ancestor',BASE,commit)==b'','Baseline ancestry differs')
 for path,blob in meta['files'].items():
  require(git('rev-parse',commit+':'+path).decode().strip()==blob,'Fresh MCP blob differs');raw=git('cat-file','blob',blob);require(gsha(raw)==blob and json.loads(raw)==load(R/path),'Complete published JSON differs');remote.append({'path':path,'git_blob':blob,'raw_sha256':sha(raw),'complete_json_equal':True})
 registry={s['path']:s for f in FOLDERS for s in load(R/f/'source-checks.json')['sources']}
 def freshcheck(item):
  path,s=item;require(s['commit']==PIN,'Unpinned source');raw=urlopen(f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/'+path,timeout=45).read();require(gsha(raw)==s['blob_sha'] and json.loads(raw)==load(H.parent/'reference'/(path.split('/')[0]+'.json')),'Fresh pinned source mismatch');return {'path':path,'git_blob':s['blob_sha'],'sha256':sha(raw),'completion_credit':0}
 with ThreadPoolExecutor(max_workers=8) as pool:fresh=list(pool.map(freshcheck,sorted(registry.items())))
out={'result':'passed','auditor':'Codex root (technical preservation checks, no additional semantic credit)','checked_at_utc':datetime.now(timezone.utc).isoformat(),'baseline_commit':BASE,'run_id':RUN,'require_staged':opt.require_staged,'published':opt.published,'completion_credit':0,'new_source_units':len(plan['supported']),'new_pairs':len(plan['rows']),'source_units_read':plan['source_units_read'],'new_deferred_source_units':len(allnewdef),'total_deferred_source_units':len(knowndef),'new_pending_target_candidates':len(allnewcases),'total_pending_target_candidates':len(knowncases),'cumulative_sources':p['completed_source_verses'],'cumulative_pairs':p['completed_cross_references'],'completed_chapters':p['completed_chapters'],'completed_books':p['completed_book_records'],'pending_books':p['pending_book_records'],'book_totals':{book:{'completed_sources':len(s['done']),'completed_pairs':len(s['edges']),'pending_sources':len(s['pending']),'deferred_sources':len(s['checks']['deferred_source_units']),'unreviewed_sources':len(s['unread'])} for book,s in states.items()},'next':p['next'],'next_unreviewed':p['next_unreviewed'],'old_psalms_completed_objects_preserved':1115,'old_psalms_pairs_preserved':1171,'old_psalms_source_deferrals_preserved':235,'old_psalms_target_cases_preserved':48,'prior_runs_preserved':36,'first_reviewed_source_units':672,'revisited_source_units_read':0,'resolved_source_deferrals_count':0,'immutable_git_objects':len(immutable),'archived_files':len(files),'raw_pin_rehashes':len(pins),'new_inventory_credit':0,'new_target_provenance_credit':0,'new_target_sources':[e['book'] for e in targetextras],'full_remote_json_readback':remote,'fresh_source_checks':fresh,'validator_reports':reports}
out['production_code_unchanged']=True
out['unavailable_target_locator_hint_count']=hintcount
out['unavailable_locator_hint_completion_credit']=0
(H/('remote-readback.json' if opt.published else 'preservation-audit.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:out[k] for k in ['result','require_staged','published','new_source_units','new_pairs','cumulative_sources','cumulative_pairs','next','next_unreviewed','completion_credit']}))
