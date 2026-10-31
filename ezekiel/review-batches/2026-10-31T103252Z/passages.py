import json,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parents[1]
INDEX={}
for f in (BASE/'reference').glob('*.json'):
    if f.stem in {'index','progress'}:continue
    data=json.loads(f.read_text(encoding='utf-8-sig'))
    book=data.get('book') if isinstance(data,dict) else f.stem.replace('-',' ').title()
    def walk(x):
        if isinstance(x,dict):
            if 'text' in x and ('reference' in x or 'ref' in x):
                r=x.get('reference') or book+' '+x['ref'];INDEX[r]={**x,'book':book,'file':f.name}
            for value in x.values():walk(value)
        elif isinstance(x,list):
            for value in x:walk(value)
    walk(data)
def keys(ref):
    if ref in INDEX:return [ref]
    m=re.fullmatch(r'(.+) (\d+):(\d+[a-z]*)(?:-(\d+[a-z]*))?',ref)
    if not m:raise ValueError(ref)
    b,c,a,z=m.groups();prefix=f'{b} {c}:';start=prefix+a
    if z is None:return [start]
    ordered=[r for r in INDEX if r.startswith(prefix)]
    end=prefix+z
    if start not in ordered or end not in ordered:raise KeyError(ref)
    first,last=ordered.index(start),ordered.index(end)
    if first>last:raise ValueError('Reversed source range: '+ref)
    return ordered[first:last+1]
def passage(ref):return [INDEX[k] for k in keys(ref)]
def complete_text(unit):return '\n'.join([unit['text']]+unit.get('continuation_paragraphs',[]))
if __name__=='__main__':
    for ref in sys.argv[1:]:
        print('\n'+ref)
        for k in keys(ref):print(k+' '+complete_text(INDEX[k]))
