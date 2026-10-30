from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,sys,subprocess
sys.stdout.reconfigure(encoding='utf-8')
H=Path(__file__).resolve().parent;REPO=H.parent/'saints-crossrefs';OUT=H/'new-psalms'
PIN='328967336f32958587835c921fea3b96a5bf6494';SHA='a2dbd7f46f72598db5607ea2617e1d330aff4b74'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
BASE='b24361e4b3b068c7a37a65c6a3575ee0b2a2b04e'
git=lambda *a:subprocess.check_output(['git',*a],cwd=REPO)
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain').strip()
assert not OUT.exists() and not (REPO/'psalms').exists()
for filename in ['psalms-seed.json','psalms-inventory-seed.json','psalms-inventory-check.json','before-psalms.json','psalms-inventory.json','inventory-psalms-receipt.json']:assert not (H/filename).exists(),filename
baseline=load(REPO/'progress.json');assert len(baseline['runs'])==34 and baseline['next']['reference']=='1 Chronicles 1:24' and baseline['next_unreviewed']['reference']=='Psalms 1:1'
assert sum(b.get('total_source_verse_units') is not None for b in baseline['books'])==20
psalmrecord=next(b for b in baseline['books'] if b['book']=='Psalms');assert psalmrecord['inventory_status']=='not yet inventoried' and psalmrecord.get('total_source_verse_units') is None
cache_bytes=(H.parent/'reference/psalms.json').read_bytes()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
mcp=load(H/'psalms-mcp-source-metadata.json');assert mcp['sha']==SHA and mcp['ref']==PIN and mcp['path']=='psalms/verses.json'
registry=[]
for folder in [b['records'].rstrip('/') for b in baseline['books'] if b.get('total_source_verse_units') is not None]:
 j=load(REPO/folder/'source-checks.json')
 registry.extend(s for s in [j['source_snapshot']]+j.get('sources',[]) if s['path']=='psalms/verses.json')
assert registry and all(s['commit']==PIN and s['blob_sha']==SHA for s in registry)
raw=(H/'psalms-pinned-source.json').read_bytes()
headers=load(H/'psalms-pinned-source-headers.json')
assert headers['raw_sha256']==hashlib.sha256(raw).hexdigest() and headers['source_blob_sha']==SHA and headers['source_commit']==PIN
assert headers['run_id']=='2026-10-30T181607Z' and headers['reviewer']=='Codex AI inventory agent /root/macc9_12_peer' and headers['response_status']==200
assert headers['metadata_sha256']==hashlib.sha256((H/'psalms-mcp-source-metadata.json').read_bytes()).hexdigest()
assert headers['complete_parsed_cache_equal'] and not headers['reference_cache_mutated']
assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==SHA
source=json.loads(raw);assert source==load(H.parent/'reference/psalms.json')
assert (H/'psalms-pinned-source.json').read_bytes()==raw
assert source['book']=='Psalms' and isinstance(source['chapters'],list)
canon=next(b for b in load(REPO/'canon.json')['books'] if b['book']=='Psalms');assert canon['order']==21
chapters=source['chapters'];units=[v for c in chapters for v in c['verses']];total=len(units);nchap=len(chapters)
assert nchap==151 and [c['chapter'] for c in chapters]==list(range(1,152)) and total==2534
assert len({v['reference'] for v in units})==len({v['id'] for v in units})==total
for c in chapters:
 for v in c['verses']:
  assert v['reference'].startswith('Psalms '+str(c['chapter'])+':') and re.match(r'\d+',v['reference'].split(':')[1]) and v['text'].strip()
  assert not {'status','cross_references'} & set(v)
continuations=[v['reference'] for v in units if v['reference'][-1].isalpha()]
nonstandard=[{'reference':v['reference'],'id':v['id'],'label_unicode_escape':v['reference'].encode('unicode_escape').decode('ascii'),'source_unit_count':1,'status':'original composite range retained as one source unit'} for c in chapters for v in c['verses'] if not re.fullmatch(r'Psalms '+str(c['chapter'])+r':\d+[a-z]*',v['reference'])]
assert all(re.fullmatch(r'Psalms \d+:\d+\u2013\d+',v['reference']) for v in nonstandard)
gaps=[]
for c in chapters:
 nums=set()
 for v in c['verses']:
  part=v['reference'].split(':')[1];combined=re.fullmatch(r'(\d+)\u2013(\d+)',part)
  if combined:nums.update(range(int(combined.group(1)),int(combined.group(2))+1))
  else:nums.add(int(re.match(r'\d+',part).group()))
 absent=sorted(set(range(1,max(nums)+1))-nums)
 if absent:gaps.append({'chapter':c['chapter'],'missing_numbers':absent})
snapshot={'repository':'Dotty777/Saints-Translation','commit':PIN,'path':'psalms/verses.json','blob_sha':SHA,'url':f'https://github.com/Dotty777/Saints-Translation/blob/{PIN}/psalms/verses.json'}
now=datetime.now(timezone.utc).isoformat()
inventory={'schema_version':1,'book':'Psalms','inventory_status':'complete for pinned source; no completion credit','inventoried':'2026-10-30','review_timezone':'America/New_York','checked_at_utc':now,'source_repository':snapshot['repository'],'source_commit':PIN,'source_path':snapshot['path'],'source_blob_sha':SHA,'source_raw_sha256':hashlib.sha256(raw).hexdigest(),'source_format':'Nested original chapters and ordered verse records. Every original book, chapter and verse field is retained; tracker status is separate from source metadata.','source_cache_check':f'All {total} original cached verse objects and the complete nested source equal the freshly fetched pinned Git blob. Inventory and technical checks add zero completed reviews.','total_chapters':nchap,'total_source_verse_units':total,'continuation_units':continuations,'numbering_gaps':gaps,'chapters':[{'chapter':c['chapter'],'source_units':len(c['verses']),'units':[{'reference':v['reference'],'source_ref':v['reference'].removeprefix('Psalms '),'id':v['id'],'text_sha256':hashlib.sha256(v['text'].encode('utf-8')).hexdigest()} for v in c['verses']]} for c in chapters]}
completion=load(REPO/'judges/verses.json')['completion_definition'];scope=load(REPO/'progress.json')['scope']
data={'schema_version':1,'edition':'Saints Bible cross-reference records','book':'Psalms','date':'2026-10-30','source_edition':'Saints Holy Bible 70-book edition, pinned Saints-Translation English records','source_status':'Supplied English records; source-edition limitations remain. No new original-language, apparatus or independent specialist verification is claimed.','source_snapshot':snapshot,'source_metadata':{'original_format':'nested chapters','original_book_metadata':{k:v for k,v in source.items() if k!='chapters'},'original_verse_fields_preserved':sorted({k for v in units for k in v}),'original_chapter_metadata_preserved':True},'review_status':'pending','completion_definition':completion,'completed_chapters':[],'completed_source_verses':0,'completed_cross_references':0,'total_chapters':nchap,'total_source_verse_units':total,'next_reference':units[0]['reference'],'readable_html':'Psalms.html','readable_text':'Psalms.txt','canon_manifest':'../canon.json','canon_policy':scope,'chapters':[{'chapter':c['chapter'],'status':'pending','source_metadata':{k:v for k,v in c.items() if k!='verses'},'verses':[{**v,'status':'pending','cross_references':[]} for v in c['verses']]} for c in chapters]}
inventory['composite_reference_units']=nonstandard
inventory['continuation_paragraph_units']=[{'reference':v['reference'],'id':v['id'],'paragraph_count':len(v['continuation_paragraphs']),'complete_text_sha256':hashlib.sha256(('\n'.join([v['text']]+v['continuation_paragraphs'])).encode('utf-8')).hexdigest()} for v in units if v.get('continuation_paragraphs')]
inventory['original_display_text_units']=[{'reference':v['reference'],'id':v['id'],'display_text_sha256':hashlib.sha256(v['display_text'].encode('utf-8')).hexdigest()} for v in units if 'display_text' in v]
inventory['original_source_fields_preserved']=True
inventory['source_status_is_provenance_only']=True
inventory['psalm_151_preserved']={'chapter':151,'source_units':len(chapters[-1]['verses']),'first_reference':chapters[-1]['verses'][0]['reference'],'last_reference':chapters[-1]['verses'][-1]['reference']}
inventory['numbering_gaps_scope']='Numeric labels not represented by an actual standalone unit or the numeric coverage of an explicitly labelled composite range. Each composite remains one original source unit; no additional verse unit or textual omission is inferred.'
save(OUT/'verses.json',data);save(OUT/'inventory.json',inventory);save(H/'psalms-seed.json',data);save(H/'psalms-inventory-seed.json',inventory)
numbering=f'Exact original nested chapter/verse order, references and anchors retained. The actual inventory contains {total} units in {nchap} chapters; continuation units and numeric gaps are recorded in inventory.json.'
save(OUT/'source-checks.json',{'schema_version':1,'book':'Psalms','date':'2026-10-30','source_snapshot':snapshot,'source_language_scope':'Supplied English records only; no new Greek, Hebrew or critical-apparatus verification.','numbering':numbering,'method':'Read complete actual source and retained target passages with necessary context and reread each particular explanation before completing a source pass. This inventory performs no source review.','completion_definition':completion,'excluded_from_completion':['Imports','Duplicate pairs','Unresolved identities','Unread candidates','Technical checks'],'review_batches':[],'canon_manifest':'../canon.json','canon_policy':scope,'sources':[snapshot],'unresolved_candidates':[],'checked_scope':{'source_passage':None,'source_verse_units':0,'retained_pairs':0,'distinct_target_verse_units':0},'inventory_evidence':{'fresh_mcp_blob_identity_verified':True,'fresh_mcp_identity':mcp,'fresh_mcp_read_scope':'Exact pinned Git blob identity; complete source parsed from freshly fetched raw Git bytes and compared with the full cache.','fresh_raw_git_blob_verified':True,'complete_parsed_cache_equal':True,'source_raw_url':f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/psalms/verses.json','raw_sha256':hashlib.sha256(raw).hexdigest(),'completed_review_credit':0},'pending':[f'Psalms 1–{nchap} initial curated cross-reference pass','Remaining Old Testament source inventories and review','Independent specialist review','Live destination anchors and reader display checks']})
save(OUT/'editorial-notes.json',{'schema_version':1,'book':'Psalms','date':'2026-10-30','notes':[{'reference':'Entire source inventory','note':f'All {total} actual units across {nchap} chapters were inventoried before source review. Every original source reference, anchor, word and metadata field is retained. The supplied source edition’s editorial and running-text statements and pending specialist checks remain provenance only; this tracker does not claim to have performed them. This inventory baseline records all units as pending, with zero completed source verses or pairs; any subsequent initial curated review is recorded separately in the tracker.'},{'reference':'Numbering','note':f'Continuation units: {len(continuations)}. Chapters with missing numeric verse numbers: {len(gaps)}. Exact ordered lists are in inventory.json; do not import another edition’s names or numbering.'}]})
(OUT/'README.md').write_text(f'''# Psalms — Saints Bible cross-references

Psalms has a complete source inventory: **{total} actual source units in {nchap} chapters**, all pending. Its initial curated pass has not started: **0 completed source verses and 0 completed pairs**. First source unit: {units[0]['reference']}. Begin at the first Psalms source unit only after this complete inventory is frozen. Previously read but uncertain units in earlier books remain pending with zero completion credit.

'''+completion+f'''

## Files

- [Psalms.html](Psalms.html): readable completed records with matching text.
- [Psalms.txt](Psalms.txt): plain text of completed records.
- [verses.json](verses.json): every original source unit and its status.
- [inventory.json](inventory.json): exact references, anchors, ordered units, continuation units, gaps and text hashes.
- [editorial-notes.json](editorial-notes.json), [source-checks.json](source-checks.json), [verification.json](verification.json): evidence and checks.
- [RESTORE.md](RESTORE.md): recovery guidance.

## Source and numbering

The counts were derived from the complete [pinned Saints-Translation record](https://github.com/Dotty777/Saints-Translation/blob/{PIN}/psalms/verses.json), verified against its exact Git blob and the complete parsed cache. Preserve all supplied book/chapter metadata, references, anchors and words. Source edition editorial status and pending specialist checks are provenance, separate from this tracker’s pending status. The inventory found {len(continuations)} continuation units and {len(gaps)} chapters with missing numeric verse numbers. Inventory adds zero completed reviews.

## Continuation

Read the current [overall tracker](../progress.json) and preserve all completed records. Begin at {units[0]['reference']} after preceding never-reviewed source units have been reviewed in order, preserving all earlier uncertain source units as pending.

## Review batches
''',encoding='utf-8')
(OUT/'RESTORE.md').write_text('''# Psalms record recovery

Read ../canon.json, ../progress.json, verses.json and inventory.json first. Fetch current remote main and preserve every completed object and review batch. Never run an initial bootstrap builder over this tracker.

Recover the source from the exact commit and blob in source-checks.json. Preserve all original nested book/chapter metadata, ordered verse objects, references, anchors and words. Tracker status is separate from earlier source-edition status. Use the actual inventory for counts, continuation units and gaps; do not replace supplied names or numbering with another edition.

Recover through Git history in a new commit. Recompute counts and the first unfinished source unit. Inventory/import, duplicates, unresolved evidence and technical checks add no review credit. Run python scripts/render_books.py and then python scripts/validate.py --write-verification from the repository root. WordPress and Saints-Translation are separate from this tracker.
''',encoding='utf-8')
if nonstandard:
 notes=load(OUT/'editorial-notes.json')
 notes['notes'].append({'reference':'Original composite source unit','note':'The source contains the exact composite label '+', '.join(x['reference'] for x in nonstandard)+', using the U+2013 en dash. It remains one inventoried source object at its original anchor. Its declared numeric coverage is considered when reporting gaps, but no extra verse units are created and its reference is not rewritten.'})
 save(OUT/'editorial-notes.json',notes)
 checks=load(OUT/'source-checks.json');checks['composite_reference_units']=nonstandard
 checks['numbering_gaps_scope']=inventory['numbering_gaps_scope']
 checks['pending'].append('Preserve the composite source reference as one original unit without rewriting its separator or creating extra verses: '+', '.join(x['reference'] for x in nonstandard))
 save(OUT/'source-checks.json',checks)
 with (OUT/'README.md').open('a',encoding='utf-8') as f:f.write('\n## Original composite source unit\n\nThe supplied source includes '+', '.join(x['reference'] for x in nonstandard)+' with an en dash as one original source object. Its exact reference and anchor are preserved without separator changes or expansion into additional verse units. See inventory.json and editorial-notes.json.\n')
assert all(v['status']=='pending' and v['cross_references']==[] for c in data['chapters'] for v in c['verses'])
assert data['source_metadata']['original_book_metadata']=={k:v for k,v in source.items() if k!='chapters'}
for s,t in zip(chapters,data['chapters']):
 assert t['source_metadata']=={k:v for k,v in s.items() if k!='verses'}
 assert all({k:v for k,v in tv.items() if k not in ['status','cross_references']}==sv for sv,tv in zip(s['verses'],t['verses']))
assert not (REPO/'psalms').exists()
result={'book':'Psalms','source_shape':'nested chapters','source_blob_sha':SHA,'source_units':total,'chapters':nchap,'first_reference':units[0]['reference'],'last_reference':units[-1]['reference'],'continuations':continuations,'numbering_gaps':gaps,'chapter_counts':[(c['chapter'],len(c['verses'])) for c in chapters],'fresh_mcp_blob_identity_verified':True,'fresh_raw_git_blob_verified':True,'complete_parsed_cache_equal':True,'first_eight_chapters':[{'chapter':c['chapter'],'source_units':len(c['verses']),'first_reference':c['verses'][0]['reference'],'last_reference':c['verses'][-1]['reference']} for c in chapters[:8]],'completed_source_verses':0,'completed_pairs':0,'repo_mutations':0,'seed_sha256':hashlib.sha256((H/'psalms-seed.json').read_bytes()).hexdigest(),'inventory_sha256':hashlib.sha256((H/'psalms-inventory-seed.json').read_bytes()).hexdigest()}
result['composite_reference_units']=nonstandard
# The check and receipt are frozen below with run, reviewer and full pin bindings.
save(H/'before-psalms.json',data);save(H/'psalms-inventory.json',inventory)
result.update(source_repository='Dotty777/Saints-Translation',source_commit=PIN,source_path='psalms/verses.json',run_id='2026-10-30T181607Z',baseline_commit='b24361e4b3b068c7a37a65c6a3575ee0b2a2b04e',inventoried='2026-10-30',review_timezone='America/New_York',checked_at_utc=now,reviewer='Codex AI inventory agent /root/macc9_12_peer',inventory_complete_before_source_review=True,source_units_read_for_semantic_review=0,completion_credit=0,source_raw_file='psalms-pinned-source.json',source_raw_sha256=hashlib.sha256(raw).hexdigest(),metadata_file='psalms-mcp-source-metadata.json',metadata_sha256=hashlib.sha256((H/'psalms-mcp-source-metadata.json').read_bytes()).hexdigest(),seed_file='before-psalms.json',inventory_file='psalms-inventory.json',all_original_source_fields_and_order_preserved=True,all_units_pending=True)
result.update(headers_file='psalms-pinned-source-headers.json',headers_sha256=hashlib.sha256((H/'psalms-pinned-source-headers.json').read_bytes()).hexdigest(),raw_bytes=len(raw),reference_cache_preexisted=True,reference_cache_mutated=False,raw_byte_equal_to_cache=raw==cache_bytes,metadata_origin='Fresh MCP metadata supplied by ROOT in this run and independently matched to own fresh full raw/header fetch.',first_fifty_chapters=[{'chapter':c['chapter'],'source_units':len(c['verses']),'first_reference':c['verses'][0]['reference'],'last_reference':c['verses'][-1]['reference']} for c in chapters[:50]],continuation_paragraph_units=inventory['continuation_paragraph_units'],original_display_text_units=inventory['original_display_text_units'],psalm_151_preserved=inventory['psalm_151_preserved'],book_metadata_preserved=data['source_metadata']['original_book_metadata'],source_book_metadata_keys=sorted(data['source_metadata']['original_book_metadata']),source_chapter_metadata_keys=sorted({k for c in chapters for k in c if k!='verses'}),source_unit_keys=sorted({k for v in units for k in v}))
save(H/'psalms-inventory-check.json',result)
save(H/'inventory-psalms-receipt.json',result)
assert load(REPO/'progress.json')==baseline and (H.parent/'reference/psalms.json').read_bytes()==cache_bytes and git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain').strip()
assert load(OUT/'verses.json')==load(H/'psalms-seed.json')==load(H/'before-psalms.json')
assert load(OUT/'inventory.json')==load(H/'psalms-inventory-seed.json')==load(H/'psalms-inventory.json')
print(json.dumps({k:result[k] for k in ['book','source_units','chapters','first_reference','last_reference','continuations','numbering_gaps','composite_reference_units','continuation_paragraph_units','original_display_text_units','first_fifty_chapters','seed_sha256','inventory_sha256','source_raw_sha256','headers_sha256','psalm_151_preserved','source_units_read_for_semantic_review','completion_credit']},ensure_ascii=False))
