"""Build zero-credit cases from manually authored source decisions after actual reading."""
from pathlib import Path
import json,sys
from passages import INDEX,keys,complete_text
H=Path(__file__).parent;S=sys.argv[1]
def get(n):return json.loads((H/n).read_text(encoding='utf-8'))
L=get(S+'-reading-log.json');I=get(S+'-cases-input.json');book=L['source_book']
def source(ref,reason):
 r=ref if ref in L['source_references'] else book+' '+ref
 assert r in L['source_references'] and L['units'][r]==complete_text(INDEX[r])
 return dict(source_reference=r,source_text=L['units'][r],reason=reason,source_unit_read=True,completed_source_credit=0,completed_pair_credit=0)
K=dict(deferred_source_units=[source(r,x) for r,x in I['deferred'].items()],unresolved_candidates=[],unread_hints=[])
for r,target,reason in I['candidates']:
 for k in keys(target):assert L['units'].get(k)==complete_text(INDEX[k]),'Candidate target must have been actually read and acknowledged.'
 K['unresolved_candidates'].append(dict(**source(r,reason),target=target,target_units=[dict(reference=k,text=L['units'][k]) for k in keys(target)],source_and_target_read=True,target_passage_read=True,retained=False))
assert not I.get('hints',[]),'Unread hints require explicit availability evidence and separate handling.'
(H/(S+'-cases.json')).write_text(json.dumps(K,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:len(v) for k,v in K.items()}))
