"""Refresh Genesis reading views and current README counts from saved records."""
from pathlib import Path
import html,json,re

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'genesis'
data=json.loads((BOOK/'verses.json').read_text(encoding='utf-8'))
progress=json.loads((ROOT/'progress.json').read_text(encoding='utf-8'))
verses=[v for c in data['chapters'] for v in c['verses'] if v['status']=='completed']
count=len(verses);pairs=sum(len(v['cross_references']) for v in verses)
first,last=verses[0]['reference'],verses[-1]['reference']
next_ref=data['next_reference'];last_chapter=data['completed_chapters'][-1]
scope=f'{first}–{last.removeprefix("Genesis ")}'
summary=f'{scope} · {count} completed verses · {pairs} completed pairs'
e=html.escape
text=['Genesis — Saints Bible cross-references',f'Completed: {scope}. Next: {next_ref}.',
      f'{count} completed source verses; {pairs} completed cross-reference pairs.',
      data['completion_definition'],'Reference edition: Bespoke Saints English Translation. Greek-based source numbering is retained.','']
sections=[]
for v in verses:
    text.extend([v['reference'],v['text']]);items=[]
    for edge in v['cross_references']:
        text.append('  '+edge['target']+' — '+edge['relationship']+': '+edge['rationale'])
        quoted=''.join('<p><b>'+e(t['reference'])+'</b> '+e(t['text'])+'</p>' for t in edge['target_verses'])
        items.append('<li><strong>'+e(edge['target'])+'</strong> <span class="kind">'+e(edge['relationship'])+'</span><p>'+e(edge['rationale'])+'</p><details><summary>Read matching passage</summary>'+quoted+'<p><a href="'+e(edge['target_source']['url'])+'">Pinned source record</a></p></details></li>')
    text.append('')
    sections.append('<section id="'+e(v['id'])+'"><h2>'+e(v['reference'])+'</h2><p class="scripture">'+e(v['text'])+'</p><ol>'+''.join(items)+'</ol></section>')
(BOOK/data['readable_text']).write_text('\n'.join(text).rstrip()+'\n',encoding='utf-8')
old=(BOOK/data['readable_html']).read_text(encoding='utf-8')
style=re.search(r'<style>(.*?)</style>',old,re.S).group(1)
nav=' · '.join('<a href="#'+e(c['verses'][0]['id'])+'">Genesis '+str(c['chapter'])+'</a>' for c in data['chapters'] if c['status']=='completed')
page='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Genesis cross-references</title><style>'+style+'</style></head><body><header><h1>Genesis cross-references</h1><p>'+e(summary)+'</p><p class="note">Initial curated pass. Next: '+e(next_ref)+'. Later source verses remain pending. Greek-based Saints-Translation numbering is retained.</p><p class="note">'+e(data['completion_definition'])+'</p><nav>'+nav+'</nav><nav><a href="README.md">Book record</a> · <a href="Genesis.txt">Plain text</a> · <a href="verses.json">Structured verse tracker</a> · <a href="../progress.json">Overall progress</a></nav></header>'+''.join(sections)+'<footer><p class="note">Latest review '+e(data['date'])+' by Codex (AI-assisted editorial review). Source: <a href="'+e(data['source_snapshot']['url'])+'">pinned Saints-Translation record</a>. Source-edition limitations continue to apply. Independent specialist and live-anchor review remain pending.</p></footer></body></html>\n'
(BOOK/data['readable_html']).write_text(page,encoding='utf-8')
readme=(BOOK/'README.md').read_text(encoding='utf-8')
current=f'Genesis 1–{last_chapter} is complete at the initial curated cross-reference stage: **{count} source verses and {pairs} distinct source/target-passage pairs**. Later chapters remain pending. Next: **{next_ref}**.'
readme=re.sub(r'\nGenesis [^\n]+\n', '\n'+current+'\n',readme,count=1)
readme=re.sub(r'start at Genesis \d+:\d+\.',f'start at {next_ref}.',readme)
if '## Review batches' not in readme:readme+='\n## Review batches\n\n'
start=readme.index('## Review batches')
links='\n'.join('- ['+r['run_id']+'](review-batches/'+r['run_id']+'.json): '+str(r['new_completed_pairs'])+' newly completed pairs across '+str(r['distinct_source_verses'])+' source verses.' for r in progress['runs'] if r.get('run_id'))
readme=readme[:start]+'## Review batches\n\n'+links+'\n'
(BOOK/'README.md').write_text(readme,encoding='utf-8')
readme=(ROOT/'README.md').read_text(encoding='utf-8')
readme=re.sub(r'^- \[Genesis[^\n]+',f'- [Genesis — 50 chapters](genesis/README.md): initial curated pass complete for chapters 1–{last_chapter}; **{count} source verses, {pairs} matching cross-reference pairs**. Later chapters remain pending.',readme,count=1,flags=re.M)
readme=re.sub(r'\*\*Next: Genesis \d+:\d+\.\*\*',f'**Next: {next_ref}.**',readme)
readme=re.sub(r'of which \d+ are completed\.',f'of which {count} are completed.',readme)
marker='\nLatest saved review: '
if marker in readme:readme=readme[:readme.index(marker)]+'\n'
run=progress['runs'][-1]
readme+=f'\nLatest saved review: {run["date"]}, **{run["new_completed_pairs"]} new pairs across {run["distinct_source_verses"]} source verses**. Hourly target: {run["hourly_target"]}; shortfall: {run.get("target_shortfall",max(0,run["hourly_target"]-run["new_completed_pairs"]))}. [Review record]({run["review_record"]}).\n'
(ROOT/'README.md').write_text(readme,encoding='utf-8')
print(json.dumps({'rendered_source_verses':count,'rendered_pairs':pairs,'next':next_ref}))
