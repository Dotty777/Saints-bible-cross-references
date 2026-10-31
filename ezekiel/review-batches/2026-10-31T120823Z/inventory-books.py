"""Technical inventory preparation only. Never writes the tracker or grants review credit."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import json, hashlib, re, urllib.request, argparse, sys
sys.stdout.reconfigure(encoding="utf-8")
H=Path(__file__).resolve().parent; R=H.parent/'saints-crossrefs'; C=H.parent/'reference'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
cfg=load(H/'run-config.json'); PIN=cfg['source_commit']; DATE=cfg['date']; RUN=cfg['run_id']; BASE=cfg['baseline_commit']
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+'\n').encode())
def inventory(stem):
 identity=load(H/(stem+'-identity.json')); rawfile=H/(stem+'-pinned-original.json')
 assert (identity['repository'],identity['ref'],identity['path'])==('Dotty777/Saints-Translation',PIN,stem+'/verses.json')
 assert not (H/('inventory-'+stem+'-receipt.json')).exists(), 'Frozen inventory already exists'
 assert not (R/stem).exists(), 'Never bootstrap over an existing book'
 names={re.sub('[^a-z0-9]+','-',book.lower()).strip('-'):book for book in cfg['new_source_books']}
 assert stem in names, 'Only an explicitly authorized new source book may be inventoried'
 canon=load(H/'before-canon.json');prior_progress=load(H/'before-progress.json')
 order=[b['book'] for b in canon['books'] if b['testament']=='Old Testament']
 first=order.index(prior_progress['next_unreviewed']['book'])
 assert cfg['source_book_sequence']==order[first:first+len(cfg['source_book_sequence'])]
 assert names[stem] in cfg['source_book_sequence'] and names[stem] not in [b['book'] for b in prior_progress['books'] if b.get('inventory_status','').startswith('complete')]
 declared=next(b for b in canon['books'] if b['book']==names[stem])
 assert declared['reference_records']==stem+'/'
 # Current-run Daniel inventory requires the full preceding Ezekiel reading gate.
 gate_path=H/'ezekiel-whole-book-source-reading-gate.json'; gate=load(gate_path)
 assert stem=='daniel' and names[stem]=='Daniel'
 assert (gate['run_id'],gate['baseline_commit'],gate['source_commit'],gate['source_book'])==(RUN,BASE,PIN,'Ezekiel')
 prior=load(H/'before-ezekiel__verses.json'); checks_before=load(H/'before-ezekiel__source-checks.json')
 prior_units=[u for c in prior['chapters'] for u in c['verses']]
 previously_read={u['reference'] for u in prior_units if u['cross_references']}|{u['source_reference'] for u in checks_before['deferred_source_units']}
 assert previously_read=={u['reference'] for u in prior_units[:1008]}
 assert gate['prior_source_units_read']==1008 and gate['current_source_units_read']==259 and gate['total_source_units']==len(prior_units)==1267
 assert gate['all_original_source_units_read'] is True and gate['completion_credit']==0
 assert gate['source_references']==[u['reference'] for u in prior_units[1008:]]
 assert len(gate['units'])==259 and gate['baseline_verses_sha256']==sha((H/'before-ezekiel__verses.json').read_bytes())
 assert gate['baseline_checks_sha256']==sha((H/'before-ezekiel__source-checks.json').read_bytes())
 assert gate['cache_sha256']==sha((C/'ezekiel.json').read_bytes())
 for recorded,u in zip(gate['units'],prior_units[1008:]):
  assert recorded['reference']==u['reference'] and recorded['complete_text']==u['text'] and recorded['text_sha256']==sha(u['text'].encode())
 # This technical inventory grants no source-reading permission. Both the preceding
 # whole-book source gate and this complete inventory are required before new-book review.
 url=f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/{stem}/verses.json'
 with urllib.request.urlopen(url,timeout=45) as resp: raw=resp.read()
 assert blob(raw)==identity['sha']; source=json.loads(raw); assert source==load(C/(stem+'.json'))
 if rawfile.exists():assert rawfile.read_bytes()==raw, 'Frozen raw bytes differ'
 else:rawfile.write_bytes(raw)
 book=source['book']; chs=source['chapters']; units=[v for c in chs for v in c['verses']]
 total=len(units); nc=len({c['chapter'] for c in chs}); ns=len(chs); now=datetime.now(timezone.utc).isoformat()
 numbered=list(dict.fromkeys(c['chapter'] for c in chs if c['chapter']>0)); prologues=[c for c in chs if c['chapter']==0]
 chapter_label=str(nc)+' native chapters'; extra={}
 if prologues:
  chapter_label=str(len(numbered))+' numbered chapters and a translator’s prologue'
  extra={'numbered_chapters':len(numbered),'numbered_chapter_numbers':numbered,'chapter_display_label':chapter_label,'prologue':{'chapter':0,'source_sections':len(prologues),'source_units':sum(len(c['verses']) for c in prologues),'source_references':[v['reference'] for c in prologues for v in c['verses']],'original_titles':[c.get('title') for c in prologues]}}
 assert len({v['reference'] for v in units})==total
 assert all(len({v['id'] for v in c['verses']})==len(c['verses']) for c in chs), 'Original IDs must be unique within their native section'
 original_id_collisions=[{'id':ident,'source_references':[v['reference'] for v in units if v['id']==ident],'source_sections':[{'section':c.get('section',i+1),'chapter':c['chapter'],'reference':v['reference']} for i,c in enumerate(chs) for v in c['verses'] if v['id']==ident]} for ident in dict.fromkeys(v['id'] for v in units) if sum(v['id']==ident for v in units)>1]
 assert all(v['text'].strip() and not {'status','cross_references'} & set(v) for v in units)
 cont=[v['reference'] for v in units if re.search(r'\d[a-z]+$',v['reference'])]
 composite=[{'reference':v['reference'],'id':v['id'],'source_unit_count':1} for v in units if ';' in v['reference'] or re.search(r':\d+[\u2013-]\d+',v['reference'])]
 nonnumeric=[{'reference':v['reference'],'id':v['id'],'source_unit_count':1} for v in units if not re.fullmatch(r'.+ \d+:\d+[a-z]*',v['reference']) and not any(x['reference']==v['reference'] for x in composite)]
 assert all(v['reference']=='Daniel 5:preface' for v in nonnumeric), 'Unexpected native nonnumeric label'
 gaps=[]
 for number in dict.fromkeys(c['chapter'] for c in chs):
  nums=set(); reference_groups=set()
  for v in [v for c in chs if c['chapter']==number for v in c['verses']]:
   if v['reference']=='Daniel 5:preface':continue
   match=re.fullmatch(r'(.+) (\d+):(\d+)(?:[\u2013-](\d+))?[a-z]*',v['reference'])
   assert match, 'Unrecognized native numeric label: '+v['reference']
   reference_groups.add((match[1],int(match[2])));first=int(match[3]);last=int(match[4] or match[3]);nums.update(range(first,last+1))
  assert len(reference_groups)==1, 'Unexpected mixed native numbering within section'
  namespace,reference_chapter=next(iter(reference_groups))
  absent=sorted(set(range(1,max(nums)+1))-nums)
  if absent:gaps.append({'chapter':number,'reference_book':namespace,'reference_chapter':reference_chapter,'missing_numbers':absent})
 snapshot={'repository':'Dotty777/Saints-Translation','commit':PIN,'path':stem+'/verses.json','blob_sha':blob(raw),'url':f'https://github.com/Dotty777/Saints-Translation/blob/{PIN}/{stem}/verses.json'}
 inv={'schema_version':1,'book':book,'inventory_status':'complete for pinned source; no completion credit','inventoried':DATE,'review_timezone':'America/New_York','checked_at_utc':now,'source_repository':snapshot['repository'],'source_commit':PIN,'source_path':snapshot['path'],'source_blob_sha':blob(raw),'source_raw_sha256':sha(raw),'source_format':'Nested original chapters and ordered verse records; every original source field retained.','source_cache_check':f'All {total} source units and complete parsed source equal the freshly fetched pinned Git blob. Zero review credit.','total_chapters':nc,'total_source_sections':ns,'total_source_verse_units':total,'continuation_units':cont,'numbering_gaps':gaps,'composite_reference_units':composite,'nonnumeric_reference_units':nonnumeric,'chapters':[{'chapter':c['chapter'],'section':c.get('section',i+1),'source_units':len(c['verses']),'units':[{'reference':v['reference'],'source_ref':v['reference'].removeprefix(book+' '),'id':v['id'],'text_sha256':sha(v['text'].encode())} for v in c['verses']]} for i,c in enumerate(chs)],'continuation_paragraph_units':[{'reference':v['reference'],'id':v['id'],'paragraph_count':len(v['continuation_paragraphs']),'complete_text_sha256':sha('\n'.join([v['text']]+v['continuation_paragraphs']).encode())} for v in units if v.get('continuation_paragraphs')],'original_display_text_units':[{'reference':v['reference'],'id':v['id'],'display_text_sha256':sha(v['display_text'].encode())} for v in units if 'display_text' in v],'original_source_fields_preserved':True,'source_status_is_provenance_only':True,'source_section_order':[{'section':c.get('section',i+1),'chapter':c['chapter'],'first_reference':c['verses'][0]['reference'],'last_reference':c['verses'][-1]['reference']} for i,c in enumerate(chs)],'numbering_gaps_scope':'Missing numeric labels within each original physical chapter group. Compound labels remain one actual unit; cross-chapter aliases remain in their original group. No missing source unit or textual omission is inferred.'}
 inv['original_anchor_collisions']=original_id_collisions
 inv['reference_namespaces']=list(dict.fromkeys(v['reference'].rsplit(' ',1)[0] for v in units))
 inv['anchor_policy']='Original IDs remain untouched; repeated IDs require unique derived readable anchors based on native section and original ID.'
 inv.update(extra)
 template_book=cfg['source_book_sequence'][0]; template_stem=re.sub('[^a-z0-9]+','-',template_book.lower()).strip('-'); template=load(H/('before-'+template_stem+'__verses.json')); data={k:deepcopy(template[k]) for k in ['schema_version','edition','source_edition','source_status','completion_definition','canon_manifest','canon_policy','chapter_status_scope']}
 data.update(book=book,date=DATE,source_snapshot=snapshot,source_metadata={'original_format':'nested chapters','original_book_metadata':{k:v for k,v in source.items() if k!='chapters'},'original_verse_fields_preserved':sorted({k for v in units for k in v}),'original_chapter_metadata_preserved':True},review_status='pending',completed_chapters=[],completed_source_sections=[],completed_source_verses=0,completed_cross_references=0,total_chapters=nc,total_source_sections=ns,total_source_verse_units=total,next_reference=units[0]['reference'],next_unreviewed_reference=units[0]['reference'],readable_html=book.replace(' ','')+'.html',readable_text=book.replace(' ','')+'.txt',chapters=[{'chapter':c['chapter'],'status':'pending','source_metadata':{k:v for k,v in c.items() if k!='verses'},'verses':[{**v,'status':'pending','cross_references':[]} for v in c['verses']]} for c in chs])
 data.update(extra)
 checks={'schema_version':1,'book':book,'date':DATE,'source_snapshot':snapshot,'source_language_scope':'Supplied English records only; no new original-language or apparatus verification.','numbering':f'Exact original order, native fields, references and anchors retained: {total} units, {chapter_label}, {ns} native source groups.','method':'Technical inventory only; no semantic review credit.','completion_definition':data['completion_definition'],'excluded_from_completion':['Imports','Duplicate pairs','Unresolved identities','Unread candidates','Technical checks'],'review_batches':[],'canon_manifest':'../canon.json','canon_policy':data['canon_policy'],'sources':[snapshot],'deferred_source_units':[],'unresolved_candidates':[],'checked_scope':{'source_passage':None,'source_units_read':0,'source_verse_units':0,'retained_pairs':0,'distinct_target_verse_units':0},'inventory_evidence':{'fresh_mcp_blob_identity_verified':True,'fresh_mcp_identity':identity,'fresh_raw_git_blob_verified':True,'complete_parsed_cache_equal':True,'source_raw_url':url,'raw_sha256':sha(raw),'completed_review_credit':0},'pending':['Initial curated review pending preceding source-order gate','Independent specialist review','Live destination anchors and reader display checks']}
 notes={'schema_version':1,'book':book,'date':DATE,'notes':[{'reference':'Entire source inventory','note':f'All {total} actual source units in {chapter_label} and {ns} native source groups were fully inventoried before source review. Original book/chapter/unit metadata, text, references, anchors, continuation units and order are preserved. Source-edition status is provenance only. All units are pending; inventory gives zero completion credit.'},{'reference':'Numbering','note':f'Continuation units: {len(cont)}; composite units: {len(composite)}; numeric-gap chapters: {len(gaps)}. Preserve exact original labels in inventory.json.'}]}
 out=H/('new-'+stem)
 for name,x in [('verses',data),('inventory',inv),('source-checks',checks),('editorial-notes',notes)]:save(out/(name+'.json'),x)
 save(H/(stem+'-seed.json'),data);save(H/(stem+'-inventory.json'),inv)
 (out/'README.md').write_text(f'# {book} - Saints Bible cross-references\n\n{book} has a complete source inventory: **{total} units in {chapter_label} and {ns} native source groups**. Inventory contributes zero completed reviews.\n\n{data["completion_definition"]}\n\n## Files\n\n- [Readable HTML]({data["readable_html"]}) and [plain text]({data["readable_text"]}).\n- [Source records](verses.json), [inventory](inventory.json), [source checks](source-checks.json), [editorial notes](editorial-notes.json), [verification](verification.json), [recovery](RESTORE.md).\n\n## Source and numbering\n\nPreserve every original reference, anchor, word, native metadata field and source section in the exact pinned order. Source-edition status is provenance only. Inventory records all continuation, composite and gap units.\n\n## Continuation\n\nRead the overall tracker before continuing. Semantic review begins only after preceding never-reviewed source units are read in canonical order.\n\n## Review batches\n',encoding='utf-8')
 (out/'RESTORE.md').write_text(f'# {book} recovery\n\nRead ../canon.json, ../progress.json, verses.json and inventory.json first. Preserve every completed object, source field, ordered unit, reference, anchor and prior review batch. Recover the exact source commit and blob in source-checks.json. Never bootstrap over existing records. Read-but-deferred units retain zero credit. Run python scripts/render_genesis.py and python scripts/validate.py --write-verification after changes.\n',encoding='utf-8')
 for orig,saved in zip(chs,data['chapters']):
  assert saved['source_metadata']=={k:v for k,v in orig.items() if k!='verses'}
  assert [{k:v for k,v in u.items() if k not in ['status','cross_references']} for u in saved['verses']]==orig['verses']
 receipt={'run_id':RUN,'baseline_commit':BASE,'source_commit':PIN,'book':book,'source_blob_sha':blob(raw),'source_raw_file':rawfile.name,'source_raw_sha256':sha(raw),'metadata_file':stem+'-identity.json','metadata_sha256':sha((H/(stem+'-identity.json')).read_bytes()),'inventory_file':stem+'-inventory.json','inventory_sha256':sha((H/(stem+'-inventory.json')).read_bytes()),'seed_file':stem+'-seed.json','seed_sha256':sha((H/(stem+'-seed.json')).read_bytes()),'checked_at_utc':now,'source_units':total,'chapters':nc,'source_sections':ns,'source_references':[v['reference'] for v in units],'source_section_order':inv['source_section_order'],'source_book_metadata_keys':sorted(data['source_metadata']['original_book_metadata']),'source_chapter_metadata_keys':sorted({k for c in chs for k in c if k!='verses'}),'source_unit_keys':sorted({k for v in units for k in v}),'continuation_units':cont,'composite_reference_units':composite,'nonnumeric_reference_units':nonnumeric,'continuation_paragraph_units':inv['continuation_paragraph_units'],'numbering_gaps':gaps,'fresh_mcp_blob_identity_verified':True,'fresh_raw_git_blob_verified':True,'complete_parsed_cache_equal':True,'all_original_source_fields_and_order_preserved':True,'inventory_complete_before_source_review':True,'source_review_gate_activated':False,'preceding_whole_book_source_gate_required_before_review':True,'source_units_read_for_semantic_review':0,'completion_credit':0,'repo_mutations':0}
 receipt['original_anchor_collisions']=original_id_collisions
 receipt['reference_namespaces']=inv['reference_namespaces']
 receipt['preceding_source_reading_gate']={'file':gate_path.name,'sha256':sha(gate_path.read_bytes()),'all_prior_book_units_read':True,'completion_credit':0}
 receipt.update(extra)
 save(H/('inventory-'+stem+'-receipt.json'),receipt)
 print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_references','source_section_order','original_anchor_collisions','continuation_units','numbering_gaps']},ensure_ascii=False))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('stems',nargs='+',choices=[re.sub('[^a-z0-9]+','-',book.lower()).strip('-') for book in cfg['new_source_books']]);args=parser.parse_args()
 for stem in args.stems:inventory(stem)
