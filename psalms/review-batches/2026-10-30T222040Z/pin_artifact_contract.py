"""Read-only recursive validation of frozen receipt pin metadata and exact raw blobs."""
from pathlib import Path
import hashlib,json

def declared_pin_metadata(value):
 if isinstance(value,dict):
  for key,item in value.items():
   if isinstance(item,str) and item.endswith('.json') and ('pin' in key.lower() or item.endswith('-pins.json')):
    expected=value.get(key+'_sha256') or value.get(key.removesuffix('_file')+'_sha256')
    assert expected,'Declared pin metadata lacks SHA256: '+key
    yield item,expected
   elif isinstance(item,(dict,list)):yield from declared_pin_metadata(item)
 elif isinstance(value,list):
  for item in value:yield from declared_pin_metadata(item)

def checked_local(here,filename,expected_sha):
 artifact=here/filename
 assert artifact.resolve().parent==here.resolve() and artifact.is_file(),filename
 assert hashlib.sha256(artifact.read_bytes()).hexdigest()==expected_sha,filename+' SHA256 differs'
 return artifact

def validated_pin_artifacts(here,receipt):
 seen=set()
 for filename,expected_sha in declared_pin_metadata(receipt):
  if (filename,expected_sha) in seen:continue
  seen.add((filename,expected_sha));metadata=checked_local(here,filename,expected_sha);yield metadata
  pins=json.loads(metadata.read_text(encoding='utf-8-sig'));assert isinstance(pins,list) and pins
  for pin in pins:
   raw_file=checked_local(here,pin['raw_file'],pin['raw_sha256']);raw=raw_file.read_bytes()
   assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==pin['blob_sha']
   assert pin['raw_git_blob_verified'] and pin['parsed_cache_equals_pinned']
   cache=here.parent/'reference'/(pin['records'].split('/')[0]+'.json')
   assert json.loads(raw)==json.loads(cache.read_bytes()),pin['book']+' complete cache differs'
   yield raw_file
