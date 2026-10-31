from pathlib import Path
import subprocess,json,hashlib,datetime
H=Path(__file__).parent;R=H.parent/'saints-crossrefs';BASE='e194517a8bdc5ceaba07142d7eafdc726480dd2c';sha=lambda b:hashlib.sha256(b).hexdigest()
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==BASE
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True)
items=[]
for p in sorted(H.glob('before-*.json')):
 if p.name=='before-proverbs.json':continue
 rel=p.name.removeprefix('before-').replace('__','/')
 raw=subprocess.check_output(['git','show',BASE+':'+rel],cwd=R)
 assert p.read_bytes()==raw,(p.name,'not exact baseline Git bytes')
 items.append({'path':rel,'snapshot_file':p.name,'sha256':sha(raw)})
progress=json.loads((H/'before-progress.json').read_bytes());ps=json.loads((H/'before-psalms__verses.json').read_bytes())
verses=[p for p in items if p['path'].endswith('/verses.json')];inventories=[p for p in items if p['path'].endswith('/inventory.json')]
assert len(verses)==21 and len(inventories)==20 and len(progress['runs'])==37
assert (progress['completed_source_verses'],progress['completed_cross_references'],progress['completed_chapters'])==(16129,20852,420)
known={v['path'].split('/')[0] for v in verses}|{'proverbs'}
paths={'canon.json','progress.json','review-batches/2026-10-30T222040Z.json'}
for folder in known:
 paths|={folder+'/verses.json',folder+'/source-checks.json'}
 if folder!='genesis':paths.add(folder+'/inventory.json')
paths|={b+'/review-batches/2026-10-30T222040Z.json' for b in ['psalms','proverbs']}
assert len(paths)==70
out={'run_id':'2026-10-30T222040Z','reviewer':'Codex AI independent technical auditor /root/macc9_12_peer','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'baseline_commit':BASE,'all_existing_before_snapshots_equal_full_baseline_git_bytes':True,'snapshot_count':len(items),'old_known_book_count':21,'old_separate_inventory_file_count':20,'old_run_count':37,'old_completed_sources':16129,'old_completed_pairs':20852,'old_completed_chapters':420,'snapshots':items,'expected_publication_json_paths':sorted(paths),'expected_publication_json_count':70,'repository_status_before_and_after':'clean','completion_credit':0}
assert not subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True)
p=H/'independent-baseline-snapshot-audit.json';assert not p.exists() or sha(p.read_bytes())=='0b7bf8593a359b15eed2807c874e35d24bc7d2f47127a9b309d1ecfd87a9f974';p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'snapshots':len(items),'expected_json_paths':70,'receipt_sha256':sha(p.read_bytes())}))
