"""Read-only contracts for this run's new Proverbs inventory and prepared code.

These checks earn no semantic credit and never mutate the repository.
"""
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, re, runpy, subprocess
from review_contract import HERE, REPO, RUN, PIN, BASE_COMMIT, load, digest
from publication_parent import PUBLICATION_PARENT,publication_contract

PRODUCTION_PATHS = {'scripts/chapter_structure.py', 'scripts/validate.py', 'scripts/render_books.py'}

def gsha(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def validate_target_headers(extra):
    headers=load(local(extra['headers_file']))
    assert digest(local(extra['headers_file']))==extra['headers_sha256'] and headers['status']==200
    url=f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/'+extra['path']
    assert headers['request_url']==headers['response_url']==url
    assert headers['source_commit']==PIN and headers['source_blob_sha']==extra['blob_sha']
    assert headers['raw_sha256']==extra['raw_sha256'] and headers['metadata_sha256']==extra['metadata_sha256']
    assert headers['completion_credit']==0 and headers['source_review_started'] is False
    assert datetime.fromisoformat(headers['checked_at_utc'])>=datetime.fromisoformat(headers['requested_at_utc'])>=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    return True

def local(name):
    p=(HERE/name).resolve()
    assert p.is_relative_to(HERE.resolve()) and p.is_file(), name
    return p

def production_contract(current_is_final=False):
    contract=load(HERE/'chapter-structure-change-contract.json')
    assert contract['run_id']==RUN and contract['baseline_commit']==BASE_COMMIT
    assert contract['completion_credit']==0 and contract['root_worktree_mutated'] is False
    assert {f['path'] for f in contract['files']}==PRODUCTION_PATHS and len(contract['files'])==3
    assert (contract['complete_book_chapters'],contract['complete_book_source_sections'])==(31,34)
    outputs={}
    for f in contract['files']:
        assert f['prepared_file']=='production-changes/'+f['path']
        p=local(f['prepared_file']); assert digest(p)==f['after_sha256']
        tracked=subprocess.check_output(['git','ls-tree',BASE_COMMIT,'--',f['path']],cwd=REPO)
        if f['before_sha256'] is None:
            assert not tracked and f['path']=='scripts/chapter_structure.py'
        else:
            raw=subprocess.check_output(['git','show',BASE_COMMIT+':'+f['path']],cwd=REPO)
            assert hashlib.sha256(raw).hexdigest()==f['before_sha256']
        if current_is_final:
            assert digest(REPO/f['path'])==f['after_sha256']
        else:
            assert (not (REPO/f['path']).exists()) if f['before_sha256'] is None else digest(REPO/f['path'])==f['before_sha256']
        compile(p.read_text(encoding='utf-8'),str(p),'exec')
        outputs[f['path']]=p.read_bytes()
    for name in ['chapter-structure-independent-final-audit.json','chapter-structure-independent-amendment-check.json']:
        audit=load(HERE/name)
        assert audit['run_id']==RUN and audit['baseline_commit']==BASE_COMMIT
        assert audit['result']=='passed' and audit['completion_credit']==audit['repository_mutations']==0
        field='contract_sha256' if name.endswith('final-audit.json') else 'final_contract_sha256'
        assert audit[field]==digest(HERE/'chapter-structure-change-contract.json')
    return contract,outputs

def bound_support_files(roots,contract):
    """Validate transitive file/hash dependencies, including exact old renderer bytes."""
    historical={("production-changes/scripts/render_books.py",contract['initial_renderer_sha256']):contract['initial_renderer_file']}
    stage=load(local('publication-parent-adapter-receipt.json'))
    assert stage['review_base_commit']==BASE_COMMIT and stage['publication_parent']==PUBLICATION_PARENT
    expected={'integrate.py','preservation-audit.py','prepare-readback.py','run_support.py'}
    assert {x['original_file'] for x in stage['changed_helpers']}==expected and len(stage['changed_helpers'])==4
    for item in stage['changed_helpers']:
        original=item['original_file'];before=item['before_file']
        assert before==original[:-3]+'-before-publication-parent.py' and item['after_file']==original
        assert digest(local(before))==item['before_sha256'] and digest(local(original))==item['after_sha256']
        historical[(original,item['before_sha256'])]=before
    first=load(local(stage['first_parent_adapter_file']))
    assert digest(local(stage['first_parent_adapter_file']))==stage['first_parent_adapter_sha256']
    assert first['review_base_commit']==BASE_COMMIT and first['publication_parent']=='0b3dba6020141e4e5536340920b510f5677e7c25'
    expected_aliases=[{'original_file':x['after_file'],'original_sha256':x['after_sha256'],'preserved_file':x['after_file'][:-3]+'-first-parent.py','preserved_sha256':x['after_sha256']} for x in first['changed_helpers']]
    expected_aliases.extend([{'original_file':first['new_guard_file'],'original_sha256':first['new_guard_sha256'],'preserved_file':'publication_parent-first-parent.py','preserved_sha256':first['new_guard_sha256']},{'original_file':first['diff_file'],'original_sha256':first['diff_sha256'],'preserved_file':'publication-parent-first-adapter.diff','preserved_sha256':first['diff_sha256']}])
    assert stage['intermediate_aliases']==expected_aliases
    for item in expected_aliases:
        assert digest(local(item['preserved_file']))==item['original_sha256']==item['preserved_sha256']
        historical[(item['original_file'],item['original_sha256'])]=item['preserved_file']
    attempt=load(local(stage['checkout_guard_attempt_file']))
    assert digest(local(stage['checkout_guard_attempt_file']))==stage['checkout_guard_attempt_sha256']
    assert attempt['review_base_commit']==BASE_COMMIT and attempt['publication_parent']==PUBLICATION_PARENT
    amended={x['after_file']:x['after_sha256'] for x in attempt['changed_helpers']}
    expected_extra=[{'original_file':name,'original_sha256':value,'preserved_file':saved,'preserved_sha256':value} for name,value,saved in [('publication_parent.py',attempt['new_guard_sha256'],'publication_parent-before-checkout-normalization.py'),('preservation-audit.py',amended['preservation-audit.py'],'preservation-audit-before-checkout-normalization.py'),('run_support.py',amended['run_support.py'],'run_support-before-checkout-normalization.py'),('publication-parent-adapter.diff',attempt['diff_sha256'],'publication-parent-before-checkout-normalization.diff')]]
    assert stage['checkout_guard_aliases']==expected_extra
    for item in expected_extra:
        assert digest(local(item['preserved_file']))==item['original_sha256']==item['preserved_sha256']
        historical[(item['original_file'],item['original_sha256'])]=item['preserved_file']
    pending=[local(n) for n in roots]; seen=set()
    def scan(node):
        if isinstance(node,list):
            for child in node: yield from scan(child)
        elif isinstance(node,dict):
            for key,value in node.items():
                if isinstance(value,str) and '://' not in value and value.endswith(('.json','.tsv','.py','.md','.diff')):
                    base=key[:-5] if key.endswith('_file') else key
                    expected=node.get(base+'_sha256') or node.get(key+'_sha256')
                    if key=='file': expected=expected or node.get('sha256')
                    if key=='prepared_file': expected=node.get('after_sha256')
                    if isinstance(expected,str) and re.fullmatch('[0-9a-f]{64}',expected):
                        actual=value
                        candidate=local(value)
                        if digest(candidate)!=expected:
                            assert (value,expected) in historical,(value,'unbound historical dependency')
                            actual=historical[(value,expected)];candidate=local(actual)
                        assert digest(candidate)==expected,(value,'dependency hash differs')
                        yield candidate
                yield from scan(value)
    while pending:
        p=pending.pop()
        if p in seen: continue
        seen.add(p)
        if p.suffix=='.json': pending.extend(scan(load(p)))
    assert len({p.name for p in seen})==len(seen),'Flat archive name collision'
    return sorted(seen)

def inventory_contract():
    receipt=load(HERE/'inventory-proverbs-receipt.json')
    assert receipt['run_id']==RUN and receipt.get('baseline_commit',receipt.get('base_commit'))==BASE_COMMIT
    assert receipt['source_commit']==PIN
    raw=local(receipt['source_raw_file']).read_bytes(); original=json.loads(raw)
    metadata=load(local(receipt['metadata_file']));headers=load(local(receipt['headers_file']))
    assert metadata=={'repository':'Dotty777/Saints-Translation','path':'proverbs/verses.json','ref':PIN,'sha':'c5f312fbf47c53c3fc5f40ecdf0dec036545587b'}
    assert gsha(raw)==metadata['sha'] and hashlib.sha256(raw).hexdigest()==receipt['source_raw_sha256']
    assert digest(local(receipt['metadata_file']))==receipt['metadata_sha256']
    assert digest(local(receipt['headers_file']))==receipt['headers_sha256'] and headers['response_status']==200
    assert headers['request_url']==headers['response_url']==f'https://raw.githubusercontent.com/Dotty777/Saints-Translation/{PIN}/proverbs/verses.json'
    assert headers['source_commit']==PIN and headers['source_blob_sha']==metadata['sha']
    assert headers['raw_sha256']==receipt['source_raw_sha256'] and headers['complete_parsed_cache_equal'] is True
    assert datetime.fromisoformat(headers['checked_at_utc'])>=datetime.strptime(RUN,'%Y-%m-%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    assert original==load(HERE.parent/'reference/proverbs.json')
    seed=load(HERE/'before-proverbs.json'); inventory=load(HERE/'proverbs-inventory.json')
    assert seed==load(HERE/'proverbs-seed.json')==load(HERE/'new-proverbs/verses.json')
    assert inventory==load(HERE/'new-proverbs/inventory.json')
    assert digest(HERE/receipt['seed_file'])==receipt['seed_sha256']==digest(HERE/'proverbs-seed.json')
    assert digest(HERE/receipt['inventory_file'])==receipt['inventory_sha256']
    assert (seed['total_source_verse_units'],seed['total_chapters'],seed['total_source_sections'])==(939,31,34)
    assert (inventory['total_source_verse_units'],inventory['total_chapters'],inventory['total_source_sections'])==(939,31,34)
    assert seed['source_metadata']['original_book_metadata']=={k:v for k,v in original.items() if k!='chapters'}
    assert [c['chapter'] for c in seed['chapters']]==list(range(1,25))+[30,24,30,31]+list(range(25,30))+[31]
    assert len(seed['chapters'])==len(original['chapters'])==len(inventory['chapters'])==34
    assert seed['completed_source_verses']==seed['completed_cross_references']==0 and seed['completed_chapters']==seed.get('completed_source_sections',[])==[]
    refs=[]
    for section,source,inv in zip(seed['chapters'],original['chapters'],inventory['chapters']):
        assert section['source_metadata']=={k:v for k,v in source.items() if k!='verses'}
        assert section['chapter']==source['chapter']==inv['chapter'] and section['status']=='pending'
        assert len(section['verses'])==len(source['verses'])==len(inv['units'])==inv['source_units']
        for unit,body,entry in zip(section['verses'],source['verses'],inv['units']):
            assert all(unit[k]==v for k,v in body.items()) and unit['status']=='pending' and unit['cross_references']==[]
            assert (entry['reference'],entry['id'],entry['text_sha256'])==(body['reference'],body['id'],hashlib.sha256(body['text'].encode()).hexdigest())
            refs.append(body['reference'])
    assert len(refs)==len(set(refs))==939 and len(inventory['continuation_units'])==48
    checks=load(HERE/'new-proverbs/source-checks.json')
    assert checks['inventory_evidence']['completed_review_credit']==0
    assert checks['inventory_evidence']['fresh_mcp_identity']==metadata
    assert not checks.get('deferred_source_units',[]) and not checks.get('unresolved_candidates',[])
    summary={'book':'Proverbs','source_units':939,'chapters':31,'total_source_sections':34,'source_blob_sha':metadata['sha'],'completion_credit':0}
    evidence={'inventory_summary':summary,'inventory_receipt_file':'inventory-proverbs-receipt.json','inventory_receipt_sha256':digest(HERE/'inventory-proverbs-receipt.json'),'inventory_check_file':'proverbs-inventory-check.json','inventory_check_sha256':digest(HERE/'proverbs-inventory-check.json'),'seed_file':'proverbs-seed.json','seed_sha256':digest(HERE/'proverbs-seed.json'),'inventory_file':'proverbs-inventory.json','inventory_sha256':digest(HERE/'proverbs-inventory.json'),'original_unit_objects_and_source_sections_preserved':True,'completion_credit':0}
    return {'inventory':inventory,'seed':seed,'summary':summary,'evidence':evidence}

def run_support(current_is_final=False):
    publication=publication_contract()
    contract,outputs=production_contract(current_is_final)
    inventory=inventory_contract()
    roots=['chapter-structure-change-contract.json','chapter-structure-independent-final-audit.json','chapter-structure-independent-amendment-check.json','inventory-proverbs-receipt.json','proverbs-inventory-check.json','before-proverbs.json','proverbs-seed.json','proverbs-inventory.json']
    roots+=['publication-parent2-reconciliation.json','publication-parent-adapter-receipt.json','concurrent-root-renderer2-check.json']
    files=bound_support_files(roots,contract)
    structure=runpy.run_path(str(local('production-changes/scripts/chapter_structure.py')))
    archive_manifest=[{'original_file':p.relative_to(HERE).as_posix(),'archive_file':p.name,'sha256':digest(p)} for p in files]
    return {'contract':contract,'production_outputs':outputs,'files':files,'inventory_records':{'Proverbs':inventory},'newfolders':{'Proverbs':HERE/'new-proverbs'},'inventories':[inventory['summary']],'inventory_evidence':[inventory['evidence']],'archive_manifest':archive_manifest,**{k:structure[k] for k in ['chapter_units','completed_chapter_numbers','completed_source_sections']}}
