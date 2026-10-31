from pathlib import Path
import sys,json,datetime
H=Path(__file__).parent;sys.path.insert(0,str(H));import incremental as m
p=m.load(H/'helper-technical-proposal.json')
assert m.digest(H/'helper-technical-proposal.json')=='1322b4506f2de85827484182a4278eb09c1753ec4259c9df66aa7365c71079eb'
for item in p['files']+p['evidence']:assert m.digest(H/item['file'])==item['sha256'],item
assert m.baseline()==m.load(H/'baseline-proof.json')
old=(H/'accepted-prior-incremental.py.raw.txt').read_text(encoding='utf-8')
expected=old.replace("    old=previously_read_refs(book)\n    return [v['reference'] for v in flat(book_data(book)) if v['status']=='pending']","    old=previously_read_refs(book)\n    considered=set(load(HERE/'before-progress.json').get('pending_evidence_review',{}).get('considered_source_references',[]))\n    return [v['reference'] for v in flat(book_data(book)) if v['status']=='pending' and v['reference'] not in considered]")
assert expected==(H/'incremental.py').read_text(encoding='utf-8')
for n in ['passages.py','build-author-cases.py']:assert (H/n).read_bytes()==(H/('accepted-prior-'+n+'.raw.txt')).read_bytes()
for path,n in [('scripts/render_books.py','production-render_books.py'),('scripts/validate.py','production-validate.py')]:assert (H/n).read_bytes().replace(b'\r\n',b'\n')==m.original(path).replace(b'\r\n',b'\n')
for n in ['book-author.py','freeze-book-author.py']:
    text=(H/n).read_text(encoding='utf-8');compile(text,n,'exec');assert "chapters=list(dict.fromkeys(chapter_by_ref[r] for r in refs))" in text
    assert text.replace("get('review-plan.json')['packets']","get('review-plan-extension.json')['packets']")==(H/('extension-'+n)).read_text(encoding='utf-8')
assert m.native_chapters('Sirach',['Sirach Prologue 1'])==[0]
prior=m.load(H/'before-progress.json');assigned=[r for p in m.PLAN['packets'] for r in p['candidate_source_references']]
assert len(assigned)==len(set(assigned))==1130 and assigned[0]=='Psalms 40:9'
assert not set(assigned)&set(prior['pending_evidence_review']['considered_source_references'])
original=m.selection
try:
    m.selection=lambda s:{'considered_source_references':next(p for p in m.PLAN['packets'] if p['stem']==s)['candidate_source_references']}
    final=m.pending_cursor(prior,{s:{'cohort':[]} for s in m.STEMS},{})
    assert final['next_candidate'] is None and len(final['considered_source_references'])==2254 and final['actual_source_units_reread_this_run']==0
    m.selection=lambda s:{'considered_source_references':assigned[:20] if s=='psalms-pending' else []}
    partial=m.pending_cursor(prior,{s:{'cohort':[]} for s in m.STEMS},{})
    assert partial['next_candidate']['reference']=='Psalms 47:6'
    m.selection=lambda s:{'considered_source_references':[next(p for p in m.PLAN['packets'] if p['stem']==s)['candidate_source_references'][0]] if s=='ezekiel-pending' else []}
    try:m.considered_scope()
    except ValueError:pass
    else:raise AssertionError('Skipped canonical prefix accepted')
finally:m.selection=original
bind=lambda n:{'file':n,'sha256':m.digest(H/n)}
result={'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'result':'passed','reviewer':'Codex independent technical peer /root','proposal':bind('helper-technical-proposal.json'),'checker':bind(Path(__file__).name),'baseline_git_objects':216,'all_baseline_objects_parsed_and_compared':True,'only_helper_delta_is_excluding_prior_considered_refs':True,'native_Sirach_Prologue_chapter':0,'partial20_cursor':partial['next_candidate'],'final_considered_fixture_count':2254,'final_candidate_fixture':None,'skip_ahead_rejected':True,'production_scripts_unchanged':True,'completion_credit':0,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(H/'root-technical-check.json').write_bytes(m.encoded(result))
receipt={'run_id':m.RUN,'base_commit':m.BASE,'source_commit':m.PIN,'reviewer':'Codex independent technical peer /root','reviewed':m.DATE,'review_timezone':'America/New_York','disposition':'accepted','outstanding_findings':[],'completion_credit':0,'files':p['files'],'evidence':p['evidence']+[bind('root-technical-check.json')],'scope':['Exact prior accepted helper compared with current exclusion delta; previous preservation, transactional apply and concurrent NT protection unchanged.','Fresh complete Git baseline, all proposal inputs, native chapter mapping and canonical consideration cursor independently checked.','Actual author and independent semantic peer reading and final source registry remain separate preconditions. No completion credit for tests, consideration or rereading.']}
(H/'technical-peer-review.json').write_bytes(m.encoded(receipt));m.declared_evidence_closure(['technical-peer-review.json'])
print(json.dumps({'result':'passed','technical_receipt_sha256':m.digest(H/'technical-peer-review.json'),'baseline_git_objects':216},indent=2))
