from pathlib import Path
import json,sys,uuid
sys.dont_write_bytecode=True
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import incremental as m
S=H/('closure-probe-'+uuid.uuid4().hex[:8]);S.mkdir();m.HERE=S
checks={}
def put(n,obj):p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(m.encoded(obj));return m.digest(p)
leaf=put('nested/leaf.json',{'zero_credit':True});put('unused.json',{'unused':True})
put('top.json',{'nested':[{'file':'nested/leaf.json','sha256':leaf}], 'same_file':'nested/leaf.json','same_sha256':leaf,'unbound_file':'unused.json'})
c=m.declared_evidence_closure(['top.json']);checks['only_explicit_transitive_exact_files']=set(c)=={'top.json','nested/leaf.json'}
checks['exact_hashes']=all(m.digest(S/n)==h for n,h in c.items())
def rejected(label,name,expected=leaf):
 put('bad.json',{'file':name,'sha256':expected})
 try:m.declared_evidence_closure(['bad.json'])
 except (ValueError,FileNotFoundError,IsADirectoryError,json.JSONDecodeError):checks[label]=True
 else:raise AssertionError(label)
for label,name in [('absolute_inside',str(S/'nested/leaf.json')),('absolute_outside',str(H/'incremental.py')),('traversal_outside','../incremental.py'),('contained_traversal','nested/../nested/leaf.json'),('backslash','nested\\leaf.json'),('double_slash','nested//leaf.json'),('dot_alias','./nested/leaf.json'),('drive_path','C:leaf.json'),('empty_path',''),('null_path',None),('missing_file','missing.json'),('directory','nested')]:rejected(label,name)
rejected('wrong_hash','nested/leaf.json','0'*64);rejected('invalid_hash','nested/leaf.json','bogus')
(S/'bad.bin').write_bytes(b'bad');rejected('unsupported_extension','bad.bin',m.digest(S/'bad.bin'))
(S/'broken.json').write_bytes(b'{');rejected('malformed_JSON','broken.json',m.digest(S/'broken.json'))
# Change the captured child immediately after its initial read; final capture check must reject it.
original_read=Path.read_bytes;changed=[False]
def changing_read(p):
 raw=original_read(p)
 if p==S/'nested/leaf.json' and not changed[0]:changed[0]=True;p.write_bytes(b'{"changed":true}')
 return raw
Path.read_bytes=changing_read
try:
 try:m.declared_evidence_closure(['top.json'])
 except ValueError:checks['changed_during_capture_rejected']=True
 else:raise AssertionError('changed capture accepted')
finally:Path.read_bytes=original_read
assert all(checks.values())
out={'run_id':m.RUN,'helper_sha256':m.digest(H/'incremental.py'),'driver_sha256':m.digest(H/'probe-evidence-closure.py'),'checks':checks,'completion_credit':0,'production_mutations':0}
(S/'result.json').write_bytes(m.encoded(out));print(json.dumps({'result':str(S/'result.json'),'checks_passed':len(checks),'helper_sha256':out['helper_sha256']}))
