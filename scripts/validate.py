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
def load(path):
    return json.loads(path.read_text(encoding='utf-8'))
def require(condition,message):
    if not condition: raise ValueError(message)
class Anchors(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.details=0;self.scripture=[];self.in_scripture=False;self.current=[]
    def handle_starttag(self,tag,attrs):
        self.ids.extend(v for k,v in attrs if k=='id')
        if tag=='details':self.details+=1
        if tag=='p' and ('class','scripture') in attrs:self.in_scripture=True;self.current=[]
    def handle_data(self,text):
        if self.in_scripture:self.current.append(text)
    def handle_endtag(self,tag):
        if tag=='p' and self.in_scripture:
            self.scripture.append(''.join(self.current));self.in_scripture=False
def validate(write_receipts=False):
    progress=load(ROOT/'progress.json')
    reports=[]
    total_pairs=total_verses=total_chapters=total_books=0
    seen_pairs=set()
    names=[b['book'] for b in progress['books']]
    require(len(names)==len(set(names)),'Duplicate book records')
    required={'Tobit','Judith','Baruch','1 Maccabees','2 Maccabees','Wisdom of Solomon','Sirach'}
    require(required.issubset(names),'Missing deuterocanonical book records')
    first_unfinished=None
    for b in progress['books']:
        file=ROOT/b['records']/'verses.json'
        if not file.exists():
            require(b['completed_source_verses']==0 and b['completed_cross_references']==0,'Missing completed book file: '+b['book'])
            continue
        data=load(file)
        require(data['book']==b['book'],'Book identity mismatch')
        source_refs=set();source_ids=set();complete=[];complete_chapters=[];edges=[]
        for ch in data['chapters']:
            for v in ch['verses']:
                require(v['reference'] not in source_refs,'Duplicate source reference '+v['reference'])
                require(v['id'] not in source_ids,'Duplicate source anchor '+v['id'])
                source_refs.add(v['reference']);source_ids.add(v['id'])
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
                    require(len(e['rationale'].split())>=10,'Missing particular relationship explanation')
                    require(e['source_text_sha256']==digest(v['text']),'Source evidence hash mismatch')
                    target=e['target_source']
                    require(re.fullmatch(r'[a-f0-9]{40}',target['commit']) is not None,'Unpinned source commit')
                    require(re.fullmatch(r'[a-f0-9]{40}',target['blob_sha']) is not None,'Missing source blob identity')
                    require('/blob/'+target['commit']+'/' in target['url'],'Source URL not pinned')
                    m=re.fullmatch(r'(.+) (\d+):(\d+)(?:-(\d+))?',e['target'])
                    require(m is not None,'Unsupported target-range identity')
                    book,c,a,z=m.groups()
                    expected=[f'{book} {c}:{n}' for n in range(int(a),int(z or a)+1)]
                    require(v['reference'] not in expected,'Target contains its own source verse')
                    require(expected==[x['reference'] for x in e['target_verses']],'Missing or misordered target evidence')
                    for x in e['target_verses']:
                        require(bool(x['text'].strip()),'Empty target evidence')
                        require(x['text_sha256']==digest(x['text']),'Target evidence hash mismatch')
                    joined='\n'.join(x['reference']+' '+x['text'] for x in e['target_verses'])
                    require(e['target_passage_sha256']==digest(joined),'Target passage hash mismatch')
            all_done=all(v['status']=='completed' for v in ch['verses'])
            require((ch['status']=='completed')==all_done,'False chapter-completion claim')
            if all_done:complete_chapters.append(ch['chapter'])
        pair_keys=[(v['reference'],e['target']) for v in complete for e in v['cross_references']]
        require(len(pair_keys)==len(set(pair_keys)),'Duplicate source/target pair')
        require(len(source_refs)==data['total_source_verse_units'],'Source inventory total mismatch')
        require(len(complete)==data['completed_source_verses']==b['completed_source_verses'],'Completed verse count mismatch')
        require(len(edges)==data['completed_cross_references']==b['completed_cross_references'],'Completed pair count mismatch')
        require(complete_chapters==data['completed_chapters']==b['completed_chapters'],'Completed chapter mismatch')
        parser=Anchors();parser.feed((ROOT/b['records']/data['readable_html']).read_text(encoding='utf-8'))
        require(Counter(parser.ids)==Counter(v['id'] for v in complete),'Readable HTML/source anchor mismatch')
        require(parser.scripture==[v['text'] for v in complete],'Readable HTML changes source wording or order')
        require(parser.details==len(edges),'Readable HTML cross-reference count mismatch')
        text=(ROOT/b['records']/data['readable_text']).read_text(encoding='utf-8')
        for v in complete:
            require(v['reference']+'\n'+v['text']+'\n' in text,'Plain-text source verse missing or changed')
        report={'schema_version':1,'book':b['book'],'checked_at_utc':datetime.now(timezone.utc).isoformat(),
            'inventory_source_units':len(source_refs),'completed_source_verses':len(complete),
            'completed_chapters':complete_chapters,'completed_cross_references':len(edges),
            'unique_pair_ids':len(edges),'target_passage_identity_and_hash_checks':'passed',
            'source_evidence_hash_checks':'passed','readable_html_source_anchors':'passed',
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
    require(first_unfinished==progress['next']['reference'],'Continuation skips an unfinished source verse')
    print(json.dumps({'result':'passed','books_in_plan':len(names),'completed_source_verses':total_verses,
        'completed_pairs':total_pairs,'completed_chapters':total_chapters,'next':first_unfinished}))
    return reports
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write-verification',action='store_true')
    validate(p.parse_args().write_verification)
