"""Validate cross-reference evidence and saved progress using the standard library."""
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
def blob_digest(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode('ascii')+b'\0'+raw).hexdigest()
def load(path):
    return json.loads(path.read_text(encoding='utf-8'))
def require(condition,message):
    if not condition: raise ValueError(message)
def complete_text(unit):
    paragraphs=unit.get('continuation_paragraphs',[])
    require(isinstance(paragraphs,list) and all(isinstance(p,str) for p in paragraphs),'Invalid original continuation paragraphs: '+unit['reference'])
    return '\n'.join([unit['text']]+paragraphs)
def repository_path(relative):
    path=(ROOT/relative).resolve()
    require(path.is_relative_to(ROOT.resolve()),'Archived target source path escapes repository')
    return path
def archived_target_book(edge,book,cache):
    """Read ordered original units from a declared, byte-verified full-book snapshot."""
    batch=edge.get('review_batch')
    if not batch:return None
    require(re.fullmatch(r'[A-Za-z0-9_.-]+',batch) is not None,'Invalid target review batch')
    target=edge['target_source'];key=(batch,target['commit'],target['blob_sha'])
    if key in cache:return cache[key]
    if batch not in cache:
        manifest_path=repository_path('review-batches/'+batch+'.json')
        manifest=load(manifest_path) if manifest_path.exists() else {}
        archive=manifest.get('input_archive');declared=manifest.get('archived_input_files',[])
        blobs={};books=set()
        if archive and declared:
            require(manifest.get('source_commit')==target['commit'],'Archived target source commit mismatch')
            for item in declared:
                path=repository_path(str(Path(archive)/item['file']))
                if path.suffix!='.json':continue
                raw=path.read_bytes()
                require(hashlib.sha256(raw).hexdigest()==item['sha256'],'Archived target source SHA256 mismatch: '+item['file'])
                blobs[blob_digest(raw)]=(path,item['sha256'])
                document=json.loads(raw)
                if isinstance(document,dict) and isinstance(document.get('chapters'),list):books.add(document.get('book'))
        cache[batch]=(manifest.get('source_commit'),blobs,books)
    commit,blobs,books=cache[batch]
    require(commit in {None,target['commit']},'Archived target source commit mismatch')
    archived=blobs.get(target['blob_sha'])
    if archived is None:
        require(book not in books,'Pinned target blob differs from archived original source')
        cache[key]=None;return None
    path,sha256=archived;raw=path.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==sha256 and blob_digest(raw)==target['blob_sha'],'Archived target source bytes changed')
    original=json.loads(raw)
    require(isinstance(original,dict) and original.get('book')==book and isinstance(original.get('chapters'),list),'Archived target is not the expected full book')
    chapters={};units={};sections=set();chapter_sections={}
    chapter_counts=Counter(str(chapter['chapter']) for chapter in original['chapters'])
    for chapter in original['chapters']:
        number=str(chapter['chapter'])
        require(isinstance(chapter.get('verses'),list),'Invalid archived target chapters')
        section=chapter.get('section')
        if 'section' in chapter:
            require(type(section) is int and section>0 and section not in sections,'Invalid or duplicate archived target section')
            sections.add(section)
        require(number not in chapters or (section is not None and chapter_sections[number]),'Repeated archived target chapter requires distinct explicit sections')
        chapter_sections.setdefault(number,section is not None)
        prefix=book+' '+(number+':' if chapter_counts[number]>1 else '')
        # The pinned full Daniel book keeps its original embedded-section labels.
        embedded_prefix={
            ('13',13,'Daniel — Susanna'):'Susanna 1:',
            ('14',14,'Daniel — Bel and the Dragon'):'Bel and Dragon 1:',
        }.get((number,chapter.get('section'),chapter.get('title'))) if book=='Daniel' else None
        ordered=[]
        for unit in chapter['verses']:
            ref=unit.get('reference',unit.get('ref'))
            require(isinstance(ref,str) and bool(ref.strip()) and (ref.startswith(prefix) or (embedded_prefix is not None and re.fullmatch(re.escape(embedded_prefix)+r'\d+[a-z]*(?:[–-]\d+[a-z]*)?',ref) is not None)) and ref not in units,'Invalid archived target unit reference')
            require(isinstance(unit.get('id'),str) and isinstance(unit.get('text'),str),'Invalid archived target unit body')
            normalized=dict(unit,reference=ref);complete_text(normalized)
            ordered.append(ref);units[ref]=normalized
        # A logical chapter may occupy disjoint, interleaved source sections.
        # Keep both full-book insertion order and each chapter's source order.
        chapters.setdefault(number,[]).extend(ordered)
    cache[key]=(chapters,units)
    return cache[key]
def ordered_range(ordered,start,end):
    require(start in ordered and end in ordered,'Target endpoint absent from pinned source units')
    first,last=ordered.index(start),ordered.index(end)
    require(first<=last,'Reversed target range')
    return ordered[first:last+1]
class Anchors(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.details=0;self.scripture=[];self.in_scripture=False;self.current=[];self.target_scripture=[];self.in_target_scripture=False;self.target_current=[]
    def handle_starttag(self,tag,attrs):
        self.ids.extend(v for k,v in attrs if k=='id')
        if tag=='details':self.details+=1
        if tag=='p' and ('class','scripture') in attrs:self.in_scripture=True;self.current=[]
        if tag=='p' and ('class','target-scripture') in attrs:self.in_target_scripture=True;self.target_current=[]
    def handle_data(self,text):
        if self.in_scripture:self.current.append(text)
        if self.in_target_scripture:self.target_current.append(text)
    def handle_endtag(self,tag):
        if tag=='p' and self.in_scripture:
            self.scripture.append(''.join(self.current));self.in_scripture=False
        if tag=='p' and self.in_target_scripture:
            self.target_scripture.append(''.join(self.target_current));self.in_target_scripture=False
def validate(write_receipts=False):
    progress=load(ROOT/'progress.json')
    reports=[]
    total_pairs=total_verses=total_chapters=total_books=0
    seen_pairs=set()
    names=[b['book'] for b in progress['books']]
    require(len(names)==len(set(names)),'Duplicate book records')
    canon=load(ROOT/progress['canon_manifest'])
    canonical=canon['books'];allowed={b['book'] for b in canonical}
    require(len(canonical)==canon['book_count']==70,'Saints canon must contain exactly 70 books')
    require(len(allowed)==70,'Duplicate canonical book names')
    require([b['order'] for b in canonical]==list(range(1,71)),'Canonical order is not contiguous')
    source_books=[b for b in canonical if b['testament']=='Old Testament']
    require(len(source_books)==canon['old_testament_book_count']==43,'Old Testament canon count mismatch')
    require(len(canonical)-len(source_books)==canon['new_testament_book_count']==27,'New Testament canon count mismatch')
    require(names==[b['book'] for b in source_books],'Source plan differs from Saints Old Testament order')
    for actual,expected in zip(progress['books'],source_books):
        require(actual['order']==expected['order'] and actual['division']==expected['division'],'Source order or division mismatch')
    for division in canon['divisions']:
        members=[b for b in canonical if b['division']==division['division']]
        require(len(members)==division['book_count'],'Division count mismatch')
        require([b['order'] for b in members]==list(range(division['first_book_order'],division['last_book_order']+1)),'Division order mismatch')
    first_unfinished=None
    missing_earlier=[]
    inventories={};saved_units={};saved_unit_books={};archived_targets={}
    for record in progress['books']:
        path=ROOT/record['records']/'verses.json'
        if path.exists():
            saved=load(path)
            inventories[saved['book']]={str(ch['chapter']):[v['reference'] for v in ch['verses']] for ch in saved['chapters']}
            saved_units.update({v['reference']:v for ch in saved['chapters'] for v in ch['verses']})
            saved_unit_books.update({v['reference']:saved['book'] for ch in saved['chapters'] for v in ch['verses']})
    for b in progress['books']:
        file=ROOT/b['records']/'verses.json'
        if not file.exists():
            require(b['completed_source_verses']==0 and b['completed_cross_references']==0,'Missing completed book file: '+b['book'])
            missing_earlier.append(b['book'])
            continue
        require(not missing_earlier,'Book inventory skips earlier uninventoried books: '+', '.join(missing_earlier))
        data=load(file)
        require(data['book']==b['book'],'Book identity mismatch')
        inventory_file=ROOT/b['records']/'inventory.json'
        if inventory_file.exists():
            inventory=load(inventory_file)
            actual=[(v['reference'],v['id'],digest(v['text'])) for ch in data['chapters'] for v in ch['verses']]
            declared=[(v['reference'],v['id'],v['text_sha256']) for ch in inventory['chapters'] for v in ch['units']]
            require(actual==declared,'Source inventory wording, order or anchor mismatch')
            require(len(actual)==inventory['total_source_verse_units'],'Declared inventory total mismatch')
            require(inventory['source_commit']==data['source_snapshot']['commit'] and inventory['source_blob_sha']==data['source_snapshot']['blob_sha'],'Inventory source pin mismatch')
        source_refs=set();source_ids=set();complete=[];complete_chapters=[];edges=[]
        for ch in data['chapters']:
            for v in ch['verses']:
                require(v['reference'] not in source_refs,'Duplicate source reference '+v['reference'])
                require(v['id'] not in source_ids,'Duplicate source anchor '+v['id'])
                source_refs.add(v['reference']);source_ids.add(v['id'])
                complete_text(v)
                if 'complete_text_sha256' in v:
                    require(v['complete_text_sha256']==digest(complete_text(v)),'Complete source unit hash mismatch')
                require(v['status'] in {'completed','pending','unresolved'},'Invalid verse status')
                if v['status']=='completed':
                    require(bool(v['cross_references']),'Completed verse has no cross-references')
                    complete.append(v)
                elif first_unfinished is None:
                    first_unfinished=v['reference']
                for e in v['cross_references']:
                    require(v['status']=='completed','Unfinished verse contains completed pairs')
                    require(e['id'] not in seen_pairs,'Duplicate pair ID '+e['id'])
                    seen_pairs.add(e['id']);edges.append(e)
                    require(e['verdict']=='supported','Unreviewed verdict published as completed')
                    # Particularity is assessed in passage review; word counts demand padding of concise explanations.
                    require(isinstance(e['rationale'],str) and bool(e['rationale'].strip()),'Missing relationship explanation')
                    require(e['source_text_sha256']==digest(v['text']),'Source evidence hash mismatch')
                    if v.get('continuation_paragraphs') or 'source_complete_text_sha256' in e:
                        require(e.get('source_complete_text_sha256')==digest(complete_text(v)),'Complete source evidence hash mismatch')
                    target=e['target_source']
                    require(re.fullmatch(r'[a-f0-9]{40}',target['commit']) is not None,'Unpinned source commit')
                    require(re.fullmatch(r'[a-f0-9]{40}',target['blob_sha']) is not None,'Missing source blob identity')
                    require('/blob/'+target['commit']+'/' in target['url'],'Source URL not pinned')
                    archived_units={}
                    if e['target'] in saved_units:
                        # An exact declared unit may have an original composite label.
                        book=saved_unit_books[e['target']];expected=[e['target']]
                    else:
                        m=re.fullmatch(r'(.+) (\d+):(\d+[a-z]*)(?:-(\d+[a-z]*))?',e['target'])
                        require(m is not None,'Unsupported target-range identity')
                        book,c,a,z=m.groups()
                        if z and book in inventories:
                            ordered=inventories[book][c]
                            start,end=f'{book} {c}:{a}',f'{book} {c}:{z}'
                            expected=ordered_range(ordered,start,end)
                        elif z:
                            archived=archived_target_book(e,book,archived_targets)
                            if archived:
                                chapters,archived_units=archived
                                expected=ordered_range(chapters.get(c,[]),f'{book} {c}:{a}',f'{book} {c}:{z}')
                            else:
                                require(a.isdigit() and z.isdigit(),'A continuation range requires pinned original source units')
                                require(int(a)<=int(z),'Reversed target range')
                                expected=[f'{book} {c}:{n}' for n in range(int(a),int(z)+1)]
                        else:expected=[f'{book} {c}:{a}']
                    require(book in allowed,'Target book is outside Saints 70: '+book)
                    require(v['reference'] not in expected,'Target contains its own source verse')
                    require(expected==[x['reference'] for x in e['target_verses']],'Missing or misordered target evidence')
                    for x in e['target_verses']:
                        require(bool(x['text'].strip()),'Empty target evidence')
                        require(x['text_sha256']==digest(x['text']),'Target evidence hash mismatch')
                        original=archived_units.get(x['reference']) or saved_units.get(x['reference'])
                        if x['reference'] in archived_units:
                            require(x.get('id')==original['id'] and x['text']==original['text'],'Target evidence differs from pinned original unit')
                        if original and ('continuation_paragraphs' in original or 'continuation_paragraphs' in x):
                            require(x.get('continuation_paragraphs',[])==original.get('continuation_paragraphs',[]),'Original target continuation paragraphs missing or changed')
                        if 'continuation_paragraphs' in x or 'complete_text_sha256' in x:
                            require(x.get('complete_text_sha256')==digest(complete_text(x)),'Complete target unit hash mismatch')
                    joined='\n'.join(x['reference']+' '+x['text'] for x in e['target_verses'])
                    require(e['target_passage_sha256']==digest(joined),'Target passage hash mismatch')
                    if any(x.get('continuation_paragraphs') for x in e['target_verses']) or 'target_passage_complete_sha256' in e:
                        full='\n'.join(x['reference']+' '+complete_text(x) for x in e['target_verses'])
                        require(e.get('target_passage_complete_sha256')==digest(full),'Complete target passage hash mismatch')
            all_done=all(v['status']=='completed' for v in ch['verses'])
            require((ch['status']=='completed')==all_done,'False chapter-completion claim')
            if all_done:complete_chapters.append(ch['chapter'])
        pair_keys=[(v['reference'],e['target']) for v in complete for e in v['cross_references']]
        require(len(pair_keys)==len(set(pair_keys)),'Duplicate source/target pair')
        require(len(source_refs)==data['total_source_verse_units'],'Source inventory total mismatch')
        require(len(complete)==data['completed_source_verses']==b['completed_source_verses'],'Completed verse count mismatch')
        require(len(edges)==data['completed_cross_references']==b['completed_cross_references'],'Completed pair count mismatch')
        require(complete_chapters==data['completed_chapters']==b['completed_chapters'],'Completed chapter mismatch')
        book_next=next((v['reference'] for ch in data['chapters'] for v in ch['verses'] if v['status']!='completed'),None)
        require(data['next_reference']==b['next_reference']==book_next,'Book continuation mismatch')
        require((data['review_status']=='complete_initial_curated_pass')==(book_next is None),'Book completion status mismatch')
        parser=Anchors();parser.feed((ROOT/b['records']/data['readable_html']).read_text(encoding='utf-8'))
        require(Counter(parser.ids)==Counter(v['id'] for v in complete),'Readable HTML/source anchor mismatch')
        require(parser.scripture==[complete_text(v) for v in complete],'Readable HTML changes complete source wording or order')
        require(parser.target_scripture==[x['reference']+' '+complete_text(x) for edge in edges for x in edge['target_verses']],'Readable HTML changes complete target wording or order')
        require(parser.details==len(edges),'Readable HTML cross-reference count mismatch')
        text=(ROOT/b['records']/data['readable_text']).read_text(encoding='utf-8')
        for v in complete:
            require(v['reference']+'\n'+complete_text(v)+'\n' in text,'Plain-text complete source verse missing or changed')
        report={'schema_version':1,'book':b['book'],'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'canon_book_count':len(canonical),'source_book_order_and_divisions':'passed','target_book_membership':'passed',
            'inventory_source_units':len(source_refs),'completed_source_verses':len(complete),
            'completed_chapters':complete_chapters,'completed_cross_references':len(edges),
            'unique_pair_ids':len(edges),'target_passage_identity_and_hash_checks':'passed',
            'source_evidence_hash_checks':'passed','readable_html_source_anchors':'passed',
            'complete_source_and_target_continuation_bodies':'passed','readable_html_complete_target_text':'passed',
            'readable_html_source_text_and_pair_count':'passed','plain_text_source_coverage':'passed',
            'semantic_review':'Passage-grounded AI-assisted editorial review, recorded per pair; hash validation does not independently establish interpretation.',
            'remote_publication_readback':'verified separately after push; not established by this local validator',
            'live_destination_anchor_checks':'not performed','independent_specialist_review':'pending'}
        if write_receipts:
            (ROOT/b['records']/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        reports.append(report)
        total_pairs+=len(edges);total_verses+=len(complete);total_chapters+=len(complete_chapters)
        total_books+=int(len(complete)==len(source_refs))
    require(total_pairs==progress['completed_cross_references'],'Root pair total mismatch')
    require(total_verses==progress['completed_source_verses'],'Root verse total mismatch')
    require(total_chapters==progress['completed_chapters'],'Root chapter total mismatch')
    require(total_books==progress['completed_book_records'],'Root completed-book total mismatch')
    require(len(progress['books'])-total_books==progress['pending_book_records'],'Root pending-book total mismatch')
    require(first_unfinished==progress['next']['reference'],'Continuation skips an unfinished source verse')
    print(json.dumps({'result':'passed','canon_books':len(canonical),'books_in_plan':len(names),'completed_source_verses':total_verses,
        'completed_pairs':total_pairs,'completed_chapters':total_chapters,'next':first_unfinished}))
    return reports
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write-verification',action='store_true')
    validate(p.parse_args().write_verification)
