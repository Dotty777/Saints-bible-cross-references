from pathlib import Path
import json, hashlib, copy, datetime
H = Path(__file__).resolve().parent
load = lambda n: json.loads((H / n).read_bytes())
sha = lambda n: hashlib.sha256((H / n).read_bytes()).hexdigest()
J = load('joel-evidence-reference-repair.json')
oldnames = ['joel-1-4-reading-log.json.before-evidence-repair.txt', 'joel-1-4-review.json.before-evidence-repair.txt', 'joel-1-4-peer-review.json.before-evidence-repair.txt']
newnames = ['joel-1-4-reading-log.json', 'joel-1-4-review.json', 'joel-1-4-peer-review.json']
old = [load(n) for n in oldnames]
new = [load(n) for n in newnames]
for section in ['original_records', 'updated_records', 'protected_unchanged_records']:
    assert all(sha(x['file']) == x['sha256'] for x in J[section]), section
proof = 'joel-revelation-unavailable.json'
proofsha = sha(proof)
assert proofsha == '80269ce4c1dbaf135d52eea15e6a28859871a8896ca09b9046e20e6f88f98165'
assert load(proof)['ref'] == '328967336f32958587835c921fea3b96a5bf6494'
assert load(proof)['path'] == 'revelation/verses.json'
assert load(proof)['available'] is False and load(proof)['completion_credit'] == 0
restored = copy.deepcopy(new)
logannotation = restored[0].pop('technical_reference_repair')
assert logannotation['operator'] == 'Codex /root' and logannotation['completion_credit'] == 0
for i, ref in [(7, 'Joel 2:4'), (8, 'Joel 4:13')]:
    item = restored[0]['cases_reread'][i]
    assert item['kind'] == 'unread_hints' and item['case']['source_reference'] == ref
    assert item['case']['source_and_target_read'] is False and item['case']['completed_pair_credit'] == 0
    assert item['case']['availability_evidence'] == {'file': proof, 'sha256': proofsha}
    assert old[0]['cases_reread'][i]['case']['availability_evidence'] == {'file': 'revelation-unavailable.json', 'sha256': 'f234cc9fa90313ed8ec93a4b8ca64a04fa66ac91be066b0c528ddbabc0845e28'}
    item['case']['availability_evidence'] = old[0]['cases_reread'][i]['case']['availability_evidence']
assert restored[0] == old[0], 'Unexpected reading-log change'
for i in [1, 2]:
    annotation = restored[i].pop('technical_rebind')
    assert annotation['operator'] == 'Codex /root' and annotation['completion_credit'] == 0
    assert annotation['original_record'] == {'file': oldnames[i], 'sha256': sha(oldnames[i])}
assert new[1]['reading_log']['sha256'] == sha(newnames[0])
restored[1]['reading_log']['sha256'] = old[1]['reading_log']['sha256']
assert restored[1] == old[1], 'Unexpected author change'
for key in ['author_sha256', 'author_review_sha256']:
    assert new[2][key] == sha(newnames[1])
    restored[2][key] = old[2][key]
assert restored[2] == old[2], 'Unexpected peer change'
def diff(a,b,path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        out=[]
        for k in sorted(set(a)|set(b)):
            if k not in a: out.append({'path':list(path+(k,)), 'change':'added annotation'})
            elif k not in b: out.append({'path':list(path+(k,)), 'change':'removed'})
            else: out.extend(diff(a[k],b[k],path+(k,)))
        return out
    if isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
        return [x for i,(aa,bb) in enumerate(zip(a,b)) for x in diff(aa,bb,path+(i,))]
    return [] if a==b else [{'path':list(path),'before':a,'after':b}]
differences = {name:diff(a,b) for name,a,b in zip(newnames,old,new)}
if __name__ == '__main__':
    import sys
    result = {'accepted_technical_scope': True, 'exact_structured_differences':differences, 'protected_hashes_verified':J['protected_unchanged_records'], 'completion_credit':0}
    if '--receipt' in sys.argv:
        receipt = dict(run_id=J['run_id'], reviewer='Codex /root/amos_helper_recovery', reviewed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), disposition='accepted technical reference repair only', repair_journal={'file':'joel-evidence-reference-repair.json','sha256':sha('joel-evidence-reference-repair.json')}, original_records=J['original_records'], updated_records=J['updated_records'], protected_unchanged_records=J['protected_unchanged_records'], proof={'file':proof,'sha256':proofsha}, independent_check={'file':Path(__file__).name,'sha256':sha(Path(__file__).name)}, exact_structured_differences=differences, read_evidence_tool_outputs=['e4a72e','c83e22','ff52af'], findings=['Only two unread-hint evidence links, required dependent digests, and transparent technical annotations changed.', 'Restoring just those fields yields exact original parsed objects; full original bytes are preserved and SHA256-bound.', 'Final Joel TSV, cases, author full-triple reread, peer reading log and peer full-triple reread retain their protected SHA256 values.', 'Source text, target text, rationale, reading attestations, original semantic reviewer identities, acceptance and counts are unchanged.', 'Replacement evidence is the existing final owned proof of unavailability at the pinned Revelation source path; this is no new target reading or semantic review.'], limitations=['This technical acceptance is not an independent semantic rereview of Joel and does not make a fresh claim that Revelation target passages were read.'], completed_source_credit=0, completed_pair_credit=0, completion_credit=0)
        name='helper-joel-evidence-repair-review.json'
        (H/name).write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'file':name,'sha256':sha(name),'completion_credit':0}))
    else:
        print(json.dumps(result,ensure_ascii=False,indent=2))
