"""Validate the separate NT tracker against archived original passage evidence."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from html.parser import HTMLParser
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1];NT=ROOT/'new-testament'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def need(ok,message):
 if not ok:raise ValueError(message)
def digest(s):return hashlib.sha256(s.encode('utf-8')).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def full(v):return '\n'.join([v['text']]+v.get('continuation_paragraphs',[]))
def units(d,book=None):
 if isinstance(d,list):
  need(bool(book),'Flat original snapshot requires its canonical book identity')
  # Derive full labels in memory; the archived original bytes remain unchanged.
  return [dict(v,reference=v.get('reference') or book+' '+v['ref']) for v in d]
 return [v for c in d['chapters'] for v in c['verses']]
def path(relative):
 p=(NT/relative).resolve();need(p.is_relative_to(NT.resolve()),'Path escapes New Testament tracker');return p
class Readable(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=True);self.ids=[];self.pairs=[];self.sources=[];self.targets=[];self.capture=None;self.body=[];self.details=0;self.links=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if 'data-pair-id' in a:self.pairs.append(a['data-pair-id'])
  if tag=='details':self.details+=1
  if tag=='a':self.links.append(a.get('href',''))
  if tag=='p' and a.get('class') in ['scripture','target-scripture']:self.capture=a['class'];self.body=[]
 def handle_data(self,data):
  if self.capture:self.body.append(data)
 def handle_endtag(self,tag):
  if tag=='p' and self.capture:
   (self.sources if self.capture=='scripture' else self.targets).append(''.join(self.body));self.capture=None
def validate(write_verification=False):
 canon=load(ROOT/'canon.json');canonical=canon['books'];p=load(NT/'progress.json');allowed={b['book']:b for b in canonical}
 need(len(canonical)==len(allowed)==70 and [b['order'] for b in canonical]==list(range(1,71)),'Saints canon membership/order mismatch')
 expected=[b for b in canonical if b['testament']=='New Testament'];need(len(expected)==27,'New Testament must contain exactly 27 books')
 need([(b['order'],b['book'],b['division'],b['division_slug'],b['order_in_division'],b['source_staging_path']) for b in p['books']]==[(b['order'],b['book'],b['division'],b['division_slug'],b['order_in_division'],b['source_staging_path']) for b in expected],'New Testament plan differs from saved canon')
 need([b['division'] for b in expected]==['Salvation']*4+['Discipleship']*22+['Glory'],'New Testament division mismatch')
 need(p['canon_manifest']=='../canon.json' and p['canon_book_count']==70 and p['source_review_book_count']==27,'Canon manifest/count mismatch')
 target_unit='newly_completed_distinct_source_verses'
 need(p['target_per_hour']==500 and p['target_unit']==target_unit,'Hourly target must count 500 newly completed distinct source verses')
 manifest=load(NT/'source-snapshots'/'manifest.json');snapshots={};pins={}
 need(manifest['commit']==p['reference_snapshot_commit'],'Snapshot commit mismatch')
 for s in manifest['files']:
  slug=s['path'].split('/')[0];book=next((b['book'] for b in canonical if b['source_staging_path'].strip('/').split('/')[-1]==slug),None)
  need(book is not None and s['path']==slug+'/verses.json','Snapshot book outside canon')
  need(book not in snapshots,'Duplicate snapshot')
  need(s['repository']==p['reference_format_repository'] and s['commit']==manifest['commit'],'Snapshot provenance mismatch')
  need(s['url']==f'https://github.com/{s["repository"]}/blob/{s["commit"]}/{s["path"]}','Snapshot URL mismatch')
  raw=path(s['local_snapshot']).read_bytes();need(len(raw)==s['size'] and blob(raw)==s['blob_sha'] and hashlib.sha256(raw).hexdigest()==s['sha256'],'Original snapshot byte/hash mismatch: '+book)
  d=json.loads(raw)
  if isinstance(d,dict):need(d.get('book')==book,'Original snapshot book mismatch')
  original_units=units(d,book)
  need(len({u['reference'] for u in original_units})==len(original_units),'Duplicate original snapshot reference')
  # Expanded books may reuse an anchor in separately stored reading sections.
  sections=[original_units] if isinstance(d,list) else [c['verses'] for c in d['chapters']]
  need(all(len({u['id'] for u in section})==len(section) for section in sections),'Duplicate original snapshot anchor within a reading section')
  snapshots[book]=d;pins[book]={k:v for k,v in s.items() if k not in ['size','sha256']}
 totals=Counter();pair_ids=[];global_next=None;global_new=None;reports=[];all_reviewed=[];all_deferred=[];earlier_book_unreviewed=False;batch_decisions={};batch_source_books={};fully_read_books=[]
 for b in p['books']:
  folder=path(b['records']);record=folder/'verses.json'
  if not record.exists():
   need(b['status']=='pending' and b['total_source_verse_units'] is None and b['completed_source_verses']==b['completed_cross_references']==0 and b['completed_chapters']==[],'Uninventoried book has completion claims')
   need(b.get('reviewed_source_units',0)==0,'Uninventoried book has source-review claims')
   earlier_book_unreviewed=True
   if global_next is None:global_next={'book':b['book'],'chapter':1,'reference':b['book']+' 1:1','source_id':'v1-1'}
   if global_new is None:global_new={'book':b['book'],'chapter':1,'reference':b['book']+' 1:1','source_id':'v1-1'}
   continue
  need(b['book'] in snapshots,'Missing archived original for inventoried source book')
  d=load(record);checks=load(folder/'source-checks.json');inventory=load(folder/'inventory.json');original=snapshots[b['book']]
  need(d['book']==b['book'] and d['division']==b['division'] and d['canonical_order']==b['order'],'Book identity mismatch')
  need(d['source_snapshot']==checks['source_snapshot']==inventory['source_snapshot']==pins[b['book']],'Source pin mismatch')
  need(d['source_status']==original['source_status'] and d['source_edition']==original['edition'],'Source edition/limitations changed')
  need(checks['canon_manifest']=='../../canon.json','Book canon link mismatch')
  need(len(d['chapters'])==len(original['chapters'])==inventory['chapters'],'Chapter inventory mismatch')
  sourceunits=units(d);originalunits=units(original);need(len(sourceunits)==len(originalunits)==d['total_source_verse_units']==b['total_source_verse_units']==inventory['total_source_verse_units'],'Source inventory total mismatch')
  need(inventory['completion_credit']==0,'Inventory cannot earn review credit')
  expected_inventory=[];done=[];reviewed=[];deferred=[];all_edges=[];completed_chapters=[];reviewed_chapters=[];nextref=None;newref=None;unreviewed_gap=False
  for ch,origch in zip(d['chapters'],original['chapters']):
   for key in ['chapter','section','title','staging_page_id','staging_url']:
    need(ch.get(key)==origch.get(key),'Original chapter identity/order changed')
   need(len(ch['verses'])==len(origch['verses']),'Original chapter verse count changed')
   for v,orig in zip(ch['verses'],origch['verses']):
    for key,value in orig.items():need(v.get(key)==value,'Original source field changed: '+orig['reference']+'/'+key)
    need(v['status'] in ['pending','deferred','completed'],'Invalid source status')
    expected_inventory.append({'reference':v['reference'],'id':v['id'],'chapter':ch['chapter'],'section':ch.get('section'),'text_sha256':digest(v['text']),'complete_text_sha256':digest(full(v))})
    pos={'book':b['book'],'chapter':ch['chapter'],'reference':v['reference'],'source_id':v['id']}
    if v['status']!='completed' and nextref is None:nextref=pos
    if v['status']=='pending' and newref is None:newref=pos
    if v['status']=='pending':
     need('reviewed' not in v and not v['cross_references'],'Unreviewed unit has review/completion evidence');unreviewed_gap=True
    else:
     need(not unreviewed_gap,'Source review skips a never-reviewed unit before '+v['reference'])
     need(bool(v.get('reviewed')),'Reviewed source lacks its review date');reviewed.append(v)
    if v['status']=='deferred':need(bool(v.get('deferral_reason')) and not v['cross_references'],'Invalid source deferral');deferred.append(v)
    if v['status']!='completed':continue
    need(bool(v['cross_references']) and bool(v.get('reviewed')),'Completed source lacks retained reviewed pair');done.append(v)
    target_keys=set()
    for edge in v['cross_references']:
     need(edge['verdict']=='supported' and bool(edge['relationship'].strip()) and bool(edge['rationale'].strip()),'Missing pair verdict or explanation')
     need(edge['reviewer']=='Codex (AI-assisted editorial review)' and edge['reviewed']==v['reviewed'],'Pair review attribution mismatch')
     need(edge['source_text_sha256']==digest(v['text']) and edge['source_complete_text_sha256']==digest(full(v)),'Source hash mismatch')
     pin=edge['target_source'];book=next((book for book,s in pins.items() if s==pin),None);need(book in allowed and book in snapshots,'Missing or changed target pin')
     targetall=units(snapshots[book],book);byref={u['reference']:(i,u) for i,u in enumerate(targetall)};evidence=edge['target_verses'];need(bool(evidence),'Empty target passage')
     indices=[]
     for t in evidence:
      need(t['reference'] in byref,'Target reference absent from original snapshot');i,orig=byref[t['reference']];indices.append(i)
      for key in ['id','text','continuation_paragraphs']:need(t.get(key)==orig.get(key),'Original target body/identity changed: '+t['reference'])
      need(t['text_sha256']==digest(t['text']) and t['complete_text_sha256']==digest(full(t)),'Target unit hash mismatch')
      need(t['reference']!=v['reference'],'Pair references its own source')
     need(indices==list(range(indices[0],indices[-1]+1)),'Incomplete or misordered target range')
     label=evidence[0]['reference']+('–'+evidence[-1]['reference'].removeprefix(book+' ') if len(evidence)>1 else '')
     need(edge['target']==label,'Target display label mismatch')
     need(edge['target_passage_sha256']==digest('\n'.join(t['reference']+' '+t['text'] for t in evidence)) and edge['target_passage_complete_sha256']==digest('\n'.join(t['reference']+' '+full(t) for t in evidence)),'Target passage hash mismatch')
     key=(book,tuple(t['reference'] for t in evidence));need(key not in target_keys,'Duplicate source/target pair');target_keys.add(key)
     batch=load(path('review-batches/'+edge['review_batch']+'.json'));need(edge['id'] in batch['pair_ids'],'Pair absent from review batch')
     source_slug=allowed[b['book']]['source_staging_path'].strip('/').split('/')[-1];target_slug=allowed[book]['source_staging_path'].strip('/').split('/')[-1]
     target_ids=tuple(t['id'] for t in evidence)
     expected_id=source_slug+'-'+v['id'].removeprefix('v')+'__'+target_slug+'-'+target_ids[0].removeprefix('v')+('-'+target_ids[-1].removeprefix('v') if len(target_ids)>1 else '')
     need(edge['id']==expected_id,'Pair ID differs from its source/target identities')
     batch_decisions.setdefault(edge['review_batch'],[]).append((b['book'],v['id'],book,target_ids,edge['relationship'],edge['rationale']))
     batch_source_books.setdefault(edge['review_batch'],set()).add(b['book'])
     all_edges.append(edge);pair_ids.append(edge['id'])
   complete=all(v['status']=='completed' for v in ch['verses']);read=all(v['status']!='pending' for v in ch['verses'])
   need(ch['status']==('completed' if complete else 'reviewed_with_deferrals' if read else 'pending'),'Chapter completion claim mismatch')
   if complete:completed_chapters.append(ch['chapter'])
   if read:reviewed_chapters.append(ch['chapter'])
  need(inventory['units']==expected_inventory,'Source inventory hashes/identity mismatch')
  need(d['completed_source_verses']==b['completed_source_verses']==len(done) and d['completed_cross_references']==b['completed_cross_references']==len(all_edges),'Book completion totals mismatch')
  need(d['completed_chapters']==b['completed_chapters']==completed_chapters and d['reviewed_chapters']==reviewed_chapters,'Book chapter lists mismatch')
  need(d['reviewed_source_units']==b['reviewed_source_units']==len(reviewed),'Book review count mismatch')
  all_read=len(reviewed)==len(sourceunits)
  need(d.get('all_original_source_units_read',all_read)==b.get('all_original_source_units_read',all_read)==all_read,'Book source-reading completion claim mismatch')
  if all_read:fully_read_books.append(b['book'])
  need(not earlier_book_unreviewed or not reviewed,'Reviewed a later source book before reading every original source unit in its predecessor: '+b['book'])
  if newref:earlier_book_unreviewed=True
  need(d['next_reference']==b['next_reference']==(nextref or {}).get('reference') and d['next_unreviewed_reference']==b['next_unreviewed_reference']==(newref or {}).get('reference'),'Book continuation skips a source unit')
  need(d['review_status']==b['status']==('complete_initial_curated_pass' if not nextref else 'in_progress'),'Book review status mismatch')
  need({x['source_id']:x['reason'] for x in checks['deferred_source_units']}=={v['id']:v['deferral_reason'] for v in deferred},'Deferred source decisions mismatch')
  need(all(x['completed_source_credit']==x['completed_pair_credit']==0 for x in checks['deferred_source_units']),'Deferred source earns completion credit')
  need(checks['checked_scope']['source_units_read']==len(reviewed) and checks['checked_scope']['completed_source_verses']==len(done) and checks['checked_scope']['retained_pairs']==len(all_edges),'Source checks totals mismatch')
  html_text=(folder/d['readable_html']).read_text(encoding='utf-8');parser=Readable();parser.feed(html_text)
  need(parser.ids==[v['id'] for v in done] and parser.sources==[full(v) for v in done],'Readable HTML source identities/text/order changed')
  need(parser.pairs==[e['id'] for e in all_edges] and parser.details==len(all_edges),'Readable HTML pair count/order mismatch')
  need(parser.targets==[t['reference']+' '+full(t) for edge in all_edges for t in edge['target_verses']],'Readable HTML target text/order changed')
  for href in parser.links:
   if href.startswith('#'):need(href[1:] in parser.ids,'Broken chapter navigation')
   elif '://' not in href:
    need((folder/href).exists() or (write_verification and href=='verification.json'),'Missing readable local link: '+href)
  text=(folder/d['readable_text']).read_text(encoding='utf-8')
  for v in done:need(v['reference']+'\n'+full(v)+'\n' in text,'Plain-text source missing or changed')
  for edge in all_edges:
   need(edge['target']+' — '+edge['relationship']+': '+edge['rationale'] in text,'Plain-text explanation missing')
   for t in edge['target_verses']:need('    '+t['reference']+' '+full(t).replace('\n','\n    ')+'\n' in text,'Plain-text target missing or changed')
  if nextref and global_next is None:global_next=nextref
  if newref and global_new is None:global_new=newref
  totals.update(verses=len(done),pairs=len(all_edges),chapters=len(completed_chapters),reviewed=len(reviewed),deferred=len(deferred),books=int(not nextref));all_reviewed.extend(v['reference'] for v in reviewed);all_deferred.extend(v['reference'] for v in deferred)
  report={'schema_version':1,'book':b['book'],'checked_at_utc':datetime.now(timezone.utc).isoformat(),'result':'passed','canon_and_division_order':'passed','original_full_book_snapshot_git_blobs':'passed','complete_source_inventory_wording_and_anchors':'passed','complete_target_passage_identity_wording_order_and_hashes':'passed','unique_pair_ids':'passed','readable_html_source_target_text_and_pair_count':'passed','plain_text_source_target_passages_and_explanations':'passed','completed_source_verses':len(done),'completed_cross_references':len(all_edges),'completed_chapters':completed_chapters,'reviewed_source_units':len(reviewed),'deferred_source_units':len(deferred),'next_reference':(nextref or {}).get('reference'),'next_unreviewed_reference':(newref or {}).get('reference'),'semantic_review':'AI-assisted passage review recorded per pair; technical validation does not independently establish the interpretation.','independent_specialist_review':'pending','live_destination_anchor_checks':'not performed','remote_commit_readback':'performed separately after publication; not established by this validator'}
  report['all_original_source_units_read']=all_read
  report['archived_peer_review_coverage_and_resolutions']='passed'
  report['hourly_target']=p['target_per_hour'];report['target_unit']=p['target_unit'];report['latest_target_result']=p['latest_target_result']
  inputs=[ROOT/'canon.json',NT/'progress.json',NT/'source-snapshots'/'manifest.json']+[folder/name for name in ['verses.json','inventory.json','source-checks.json','editorial-notes.json','README.md','RESTORE.md',d['readable_html'],d['readable_text']]]
  for run in p['runs']:
   batch_file=path('review-batches/'+run['run_id']+'.json');inputs.append(batch_file)
   saved_batch=load(batch_file)
   inputs.extend(path('review-batches/'+relative) for relative in saved_batch['proposal_files'])
   for relative in saved_batch.get('peer_review_files',[]):
    peer_file=path('review-batches/'+relative);need(peer_file.exists(),'Missing declared peer-review archive');inputs.append(peer_file)
  report['checked_file_sha256']={f.relative_to(ROOT).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs}
  report['root_tracker_pointer_sha256']=digest(json.dumps(load(ROOT/'progress.json')['new_testament_tracker'],ensure_ascii=False,sort_keys=True))
  if not write_verification:
   verification=folder/'verification.json';need(verification.exists(),'Missing verification.json; run with --write-verification after rendering')
   saved=load(verification);need({k:v for k,v in saved.items() if k!='checked_at_utc'}=={k:v for k,v in report.items() if k!='checked_at_utc'},'Stale verification.json; run with --write-verification after rendering')
  reports.append((folder/'verification.json',report))
 need(len(pair_ids)==len(set(pair_ids)),'Duplicate pair IDs')
 for key,val in [('completed_source_verses','verses'),('completed_cross_references','pairs'),('completed_chapters','chapters'),('reviewed_source_units','reviewed'),('deferred_source_units_count','deferred'),('completed_book_records','books')]:need(p[key]==totals[val],'New Testament total mismatch: '+key)
 need(p['pending_book_records']==27-totals['books'] and p['new_testament_complete']==(totals['books']==27),'New Testament completion claim mismatch')
 need(p['next']==global_next and p['next_unreviewed']==global_new,'New Testament continuation mismatch')
 need(p.get('fully_read_source_books',fully_read_books)==fully_read_books,'Fully-read source-book list mismatch')
 rootpointer=load(ROOT/'progress.json')['new_testament_tracker'];need(rootpointer['completed_source_verses']==totals['verses'] and rootpointer['completed_cross_references']==totals['pairs'] and rootpointer['next']==global_next and rootpointer['next_unreviewed']==global_new,'Root New Testament pointer stale')
 need(rootpointer['target_per_hour']==500 and rootpointer['target_unit']==target_unit and rootpointer['latest_target_result']==p['latest_target_result'],'Root New Testament target pointer stale')
 need(rootpointer.get('fully_read_source_books',fully_read_books)==fully_read_books,'Root fully-read source-book pointer stale')
 savedpairs=[];completed_sources_seen=set()
 for run in p['runs']:
  batch=load(path('review-batches/'+run['run_id']+'.json'));need(batch==run,'Progress run differs from review record');savedpairs.extend(batch['pair_ids'])
  need(batch['new_completed_pairs']==len(batch['pair_ids']),'Batch pair total mismatch')
  credit=batch['new_completed_source_verses']
  need(batch['target_per_hour']==500 and batch['target_unit']==target_unit and batch['target_count']==credit,'Hourly target count differs from distinct completed source verses')
  need(batch['target_met']==(credit>=500) and batch['target_shortfall']==max(0,500-credit) and batch['target_excess']==max(0,credit-500),'Hourly target result or shortfall mismatch')
  proposal_units=[];proposed_pairs=[];deferred_ids=[];reviewed_decisions=[]
  peer_files=batch.get('peer_review_files',[])
  need(isinstance(peer_files,list) and len(peer_files)==len(batch['proposal_files']),'Peer-review archive coverage mismatch')
  for proposal_index,relative in enumerate(batch['proposal_files']):
   proposal=load(path('review-batches/'+relative));proposal_units.extend(proposal['reviewed_chapters'])
   peer=load(path('review-batches/'+peer_files[proposal_index]))
   peer_count=peer.get('retained_pairs_checked',peer.get('pairs_read',peer.get('pair_count_reviewed')))
   need(peer_count==len(proposal['pairs']),'Peer-review retained-pair coverage mismatch')
   for field in ['findings','material_findings','optional_wording_suggestions']:
    findings=peer.get(field,[]);need(isinstance(findings,list),'Invalid peer-review findings')
    need(all(isinstance(f,dict) and bool(f.get('resolution')) for f in findings),'Unresolved archived peer-review finding')
   source_books=batch_source_books.get(run['run_id'],set());source_book=proposal.get('source_book') or (next(iter(source_books)) if len(source_books)==1 else None)
   need(source_book in {x['book'] for x in expected},'Proposal must identify its canonical New Testament source book when a batch spans books')
   need(source_book in snapshots,'Proposal source book lacks an archived original')
   original_source=snapshots[source_book];need(isinstance(original_source,dict),'Proposal source chapters require a chapter-structured original')
   chapter_ids=[v['id'] for c in original_source['chapters'] if c['chapter'] in proposal['reviewed_chapters'] for v in c['verses']]
   reviewed_ids=proposal.get('reviewed_source_ids',chapter_ids)
   need(set(proposal['reviewed_chapters']).issubset({c['chapter'] for c in original_source['chapters']}),'Proposal names an absent source chapter')
   need(len(reviewed_ids)==len(set(reviewed_ids)) and set(reviewed_ids).issubset(chapter_ids),'Proposal reviewed source identities are duplicated or outside its declared chapters')
   paired_ids={x['source_id'] for x in proposal['pairs']};pending_ids={x['source_id'] for x in proposal.get('deferred',[])}
   need(paired_ids.isdisjoint(pending_ids) and paired_ids|pending_ids==set(reviewed_ids),'Proposal does not preserve one explicit completed-or-deferred decision for every reviewed source')
   reviewed_decisions.extend((source_book,source_id) for source_id in reviewed_ids)
   deferred_ids.extend((source_book,x['source_id']) for x in proposal.get('deferred',[]))
   proposed_pairs.extend((source_book,x['source_id'],x['target_book'],tuple(x['target_ids']),x['relationship'],x['rationale']) for x in proposal['pairs'])
  need(len(proposed_pairs)==batch['new_completed_pairs'],'Batch proposal count mismatch')
  need(Counter(proposed_pairs)==Counter(batch_decisions.get(run['run_id'],[])),'Archived proposals differ from saved pair source/target identities, relationships or rationales')
  need(len(reviewed_decisions)==len(set(reviewed_decisions))==batch['source_units_read'],'Batch reviewed source count/coverage mismatch')
  need(len(deferred_ids)==len(set(deferred_ids))==batch['deferred_source_units_count'] and len(set((x[0],x[1]) for x in proposed_pairs))==batch['new_completed_source_verses'],'Batch source decision count mismatch')
  new_sources={(x[0],x[1]) for x in proposed_pairs}
  need(new_sources.isdisjoint(completed_sources_seen),'Previously completed source verses cannot earn new-source target credit again')
  completed_sources_seen.update(new_sources)
 need(Counter(savedpairs)==Counter(pair_ids),'Review history does not cover each retained pair exactly once')
 last=p['runs'][-1]
 need(p['latest_target_result']=={k:last[k] for k in ['run_id','target_per_hour','target_unit','target_count','target_met','target_shortfall','target_excess']},'Latest hourly target result stale')
 if write_verification:
  for file,report in reports:file.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({'result':'passed','canonical_books':70,'new_testament_source_books':27,'verified_original_snapshots':len(snapshots),'completed_source_verses':totals['verses'],'completed_pairs':totals['pairs'],'completed_chapters':totals['chapters'],'deferred_source_units':totals['deferred'],'next':global_next,'next_unreviewed':global_new}))
 return reports
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--write-verification',action='store_true');validate(parser.parse_args().write_verification)
