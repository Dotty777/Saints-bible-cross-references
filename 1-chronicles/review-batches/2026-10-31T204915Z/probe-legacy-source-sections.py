"""Exercise the two real reporting expressions against native legacy records; no writes outside H."""
import ast,hashlib,json,datetime
from pathlib import Path
H=Path(__file__).parent
def sha(n):return hashlib.sha256((H/n).read_bytes()).hexdigest()
tree=ast.parse((H/'incremental.py').read_text(encoding='utf-8'))
calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='data' and n.func.attr=='get' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='total_source_sections']
assert len(calls)==2
sites=[]
for n in ast.walk(tree):
 if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='record' and n.func.attr=='update':
  sites += [k.value for k in n.keywords if k.arg=='total_source_sections']
for n in ast.walk(tree):
 if isinstance(n,ast.JoinedStr) and any(isinstance(p,ast.Constant) and isinstance(p.value,str) and 'native source groups remain unchanged' in p.value for p in n.values):
  sites += [p.value for p in n.values if isinstance(p,ast.FormattedValue) and p.value in calls]
assert len(sites)==2 and set(map(id,sites))==set(map(id,calls))
results=[]
for book in ['Esther','Job','Psalms','Daniel']:
 name='before-'+book.lower()+'__verses.json';raw=(H/name).read_bytes();data=json.loads(raw);before=json.dumps(data,sort_keys=True)
 observed=[eval(compile(ast.Expression(n),'<real reporting expression>','eval'),{'data':data,'len':len}) for n in sites]
 assert observed==[len(data['chapters'])]*2
 assert json.dumps(data,sort_keys=True)==before and (H/name).read_bytes()==raw
 if book in ['Esther','Job','Psalms']:assert 'total_source_sections' not in data
 results.append({'book':book,'optional_total_present':'total_source_sections' in data,'native_source_groups':len(data['chapters']),'distinct_native_chapters':len({c['chapter'] for c in data['chapters']}),'progress_and_recovery_counts':observed,'source_bytes_unchanged':True})
result={'run_id':'2026-10-31T204915Z','helper_sha256':sha('incremental.py'),'probe_sha256':sha(Path(__file__).name),'result':'passed','actual_helper_sites':['record.update total_source_sections','RESTORE native source groups'],'checks':results,'normalizes_optional_book_metadata':False,'production_writes':0,'completion_credit':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'legacy-source-sections-probe-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
