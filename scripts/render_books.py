"""Render inventoried books and root counts without modifying review evidence."""
from pathlib import Path
import html,json,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,s):p.write_text(s.rstrip()+'\n',encoding='utf-8')
def complete_text(unit):
    paragraphs=unit.get('continuation_paragraphs',[])
    if not isinstance(paragraphs,list) or not all(isinstance(p,str) for p in paragraphs):
        raise ValueError('Invalid original continuation paragraphs: '+unit['reference'])
    return '\n'.join([unit['text']]+paragraphs)

def render_book(record,progress,style):
    folder=ROOT/record['records'];data=load(folder/'verses.json');name=data['book']
    checks=load(folder/'source-checks.json');waiting=checks.get('unresolved_candidates',[])
    verses=[v for c in data['chapters'] for v in c['verses'] if v['status']=='completed']
    count=len(verses);pairs=sum(len(v['cross_references']) for v in verses)
    finished=count==data['total_source_verse_units'];next_ref=data['next_reference']
    deferred_set={case['source_reference'] for case in checks.get('deferred_source_units',[])}
    pending=[v['reference'] for c in data['chapters'] for v in c['verses'] if v['status']!='completed']
    deferred=[ref for ref in pending if ref in deferred_set]
    next_unreviewed=next((ref for ref in pending if ref not in deferred_set),None)
    deferred_note=(f'{len(deferred)} read source unit(s) remain deferred with zero completion credit: '+', '.join(deferred)+'. First pending source unit: '+str(next_ref)+'. '+('Never-reviewed source units start at '+next_unreviewed+'.' if next_unreviewed else 'No never-reviewed source units remain.')) if deferred else ''
    global_unreviewed=(progress.get('next_unreviewed') or {}).get('reference')
    if deferred and not next_unreviewed and global_unreviewed:deferred_note+=' Next new source review: '+global_unreviewed+'.'
    global_next=(progress.get('next') or {}).get('reference')
    continuation=('Book initial curated pass complete. Overall next: '+str(global_next)+'.') if finished else ('Next: '+str(next_ref)+'. Later source verses remain pending.')
    scope=(verses[0]['reference']+'–'+verses[-1]['reference'].removeprefix(name+' ')) if verses else 'No source verses reviewed yet'
    e=html.escape
    text=[name+' — Saints Bible cross-references',('Completed entries within: ' if deferred else 'Completed: ')+scope+'. '+continuation,
          f'{count} completed source verses; {pairs} completed cross-reference pairs.',data['completion_definition'],
          'Reference edition: '+data['source_edition']+'. Greek-based source numbering is retained.','']
    if deferred:text.insert(3,deferred_note)
    if waiting:text.insert(4,f'{len(waiting)} target candidate(s) await source evidence or identity review and are excluded from completed pair totals; see source-checks.json.')
    sections=[]
    for v in verses:
        text.extend([v['reference'],complete_text(v)]);items=[]
        for edge in v['cross_references']:
            text.append('  '+edge['target']+' — '+edge['relationship']+': '+edge['rationale'])
            quoted=''.join('<p class="target-scripture"'+(' style="white-space:pre-line"' if t.get('continuation_paragraphs') else '')+'><b>'+e(t['reference'])+'</b> '+e(complete_text(t))+'</p>' for t in edge['target_verses'])
            items.append('<li><strong>'+e(edge['target'])+'</strong> <span class="kind">'+e(edge['relationship'])+'</span><p>'+e(edge['rationale'])+'</p><details><summary>Read matching passage</summary>'+quoted+'<p><a href="'+e(edge['target_source']['url'])+'">Pinned source record</a></p></details></li>')
        text.append('');sections.append('<section id="'+e(v['id'])+'"><h2>'+e(v['reference'])+'</h2><p class="scripture"'+(' style="white-space:pre-line"' if v.get('continuation_paragraphs') else '')+'>'+e(complete_text(v))+'</p><ol>'+''.join(items)+'</ol></section>')
    write(folder/data['readable_text'],'\n'.join(text))
    nav=' · '.join('<a href="#'+e(c['verses'][0]['id'])+'">'+e(name)+' '+str(c['chapter'])+'</a>' for c in data['chapters'] if c['status']=='completed')
    summary=('Completed entries within '+scope if deferred else scope)+f' · {count} completed verses · {pairs} completed pairs'
    page='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(name)+' cross-references</title><style>'+style+'</style></head><body><header><h1>'+e(name)+' cross-references</h1><p>'+e(summary)+'</p><p class="note">Initial curated pass. '+e(continuation)+' Greek-based Saints-Translation numbering is retained.</p><p class="note">'+e(data['completion_definition'])+'</p><nav>'+nav+'</nav><nav><a href="README.md">Book record</a> · <a href="'+e(data['readable_text'])+'">Plain text</a> · <a href="verses.json">Structured verse tracker</a> · <a href="../progress.json">Overall progress</a></nav></header>'+''.join(sections)+'<footer><p class="note">Latest review '+e(data['date'])+' by Codex (AI-assisted editorial review). Source: <a href="'+e(data['source_snapshot']['url'])+'">pinned Saints-Translation record</a>. Source-edition limitations continue to apply. Independent specialist and live-anchor review remain pending.</p></footer></body></html>'
    if not verses:page=page.replace('Latest review '+e(data['date'])+' by Codex (AI-assisted editorial review).','Inventory prepared '+e(data['date'])+' by Codex. Source verse review is pending.',1)
    if waiting:page=page.replace('</header>','<p class="note">'+str(len(waiting))+' target candidate(s) await source evidence or identity review and are excluded from completed totals. <a href="source-checks.json">Pending evidence</a>.</p></header>',1)
    if deferred:page=page.replace('</header>','<p class="note">'+e(deferred_note)+' <a href="source-checks.json">Deferred source evidence</a>.</p></header>',1)
    write(folder/data['readable_html'],page)
    readme=(folder/'README.md').read_text(encoding='utf-8')
    last=data['completed_chapters'][-1] if data['completed_chapters'] else None
    coverage=f'{name} 1–{last}' if last else name
    current=f'{coverage} is complete at the initial curated cross-reference stage: **{count} source verses and {pairs} distinct source/target-passage pairs**. '+continuation
    if verses and not finished:
        chapters=', '.join(str(c) for c in data['completed_chapters']) or 'none yet'
        current=f'{name} has **{count} completed source verses and {pairs} distinct source/target-passage pairs**. Latest completed unit: **{verses[-1]["reference"]}**. Fully completed chapters: {chapters}. '+continuation
    if not verses:current=f'{name} has a complete source inventory; the initial curated pass has not started. **0 source verses and 0 completed pairs**. '+continuation
    if deferred:current+=' Completed entries within **'+scope+'**; this span includes pending source deferrals. '+deferred_note
    readme=re.sub(r'\n'+re.escape(name)+r' [^\n]+\n','\n'+current+'\n',readme,count=1)
    start=readme.index('## Continuation');end=readme.find('## Review batches',start)
    if end<0:end=len(readme)
    follow=('This book\'s initial curated pass is complete. Follow the current [overall tracker](../progress.json) for the next source verse: **'+str(global_next)+'**.') if finished else ('Read the current [overall tracker](../progress.json), preserve completed records, and start at **'+str(next_ref)+'**. Review source verses in the edition\'s order.')
    if deferred:follow+=' '+deferred_note+' Revisit these deferred units substantively before marking them complete; continue never-reviewed sources separately.'
    readme=readme[:start]+'## Continuation\n\n'+follow+' Retain only passage-grounded connections with individual explanations. A target range is one pair; unresolved identities remain pending. Preserve continuation units and source wording.\n\nSame-chapter relationships are labelled explicitly. This is an initial curated pass, not an exhaustive list of every possible cross-reference. Independent specialist and live destination checks remain pending.\n\n'+readme[end:]
    if waiting:
        readme=readme.replace('## Review batches','Pending target evidence: '+str(len(waiting))+' candidate(s), excluded from completed counts. See [source-checks.json](source-checks.json).\n\n## Review batches',1)
    links=[]
    for batch in checks.get('review_batches',[]):
        links.append('- ['+batch['run_id']+']('+batch['records']+'): '+str(batch['new_pairs'])+' newly completed pairs across '+str(batch['new_source_verses'])+' source verses.')
    marker='## Review batches'
    if marker in readme:readme=readme[:readme.index(marker)]
    write(folder/'README.md',readme.rstrip()+'\n\n'+marker+'\n\n'+'\n'.join(links))
    return {'book':name,'record':record,'units':data['total_source_verse_units'],'count':count,'pairs':pairs,'finished':finished,'last_chapter':last,'reviewed_through':verses[-1]['reference'] if verses else None,'total_chapters':len(data['chapters'])}

def main():
    progress=load(ROOT/'progress.json')
    old=(ROOT/'genesis/Genesis.html').read_text(encoding='utf-8');style=re.search(r'<style>(.*?)</style>',old,re.S).group(1)
    reports=[render_book(b,progress,style) for b in progress['books'] if (ROOT/b['records']/'verses.json').exists()]
    readme=(ROOT/'README.md').read_text(encoding='utf-8');lines=[]
    for r in reports:
        state='initial curated pass complete for all chapters' if r['finished'] else 'initial curated pass complete for chapters 1–'+str(r['last_chapter'])+'; later chapters remain pending'
        if r['count'] and not r['finished']:state='initial curated pass in progress; latest completed unit '+r['reviewed_through']
        if not r['count']:state='source inventory complete; initial curated pass pending'
        lines.append('- ['+r['book']+' — '+str(r['total_chapters'])+' chapters]('+r['record']['records']+'README.md): '+state+'; **'+str(r['count'])+' source verses, '+str(r['pairs'])+' matching cross-reference pairs**.')
    start=readme.index('- [Genesis');end=readme.index('[progress.json]',start)
    readme=readme[:start]+'\n'.join(lines)+'\n\n'+readme[end:]
    next_ref=(progress.get('next') or {}).get('reference')
    readme=re.sub(r'\*\*Next: [^\n]+?\.\*\*',f'**Next: {next_ref}.**',readme,count=1)
    readme=re.sub(r'\n\*\*Next new source review: [^\n]+?\.\*\*','',readme)
    next_unreviewed=(progress.get('next_unreviewed') or {}).get('reference')
    if next_unreviewed:readme=readme.replace(f'**Next: {next_ref}.**',f'**Next: {next_ref}.**\n**Next new source review: {next_unreviewed}.**',1)
    n=progress['completed_book_records'];completion=f'{n} Old Testament '+('book has a complete initial curated pass.' if n==1 else 'books have complete initial curated passes.')
    readme=readme.replace('No complete Old Testament book is claimed yet.',completion)
    readme=re.sub(r'\d+ Old Testament books? (?:has|have) (?:a complete initial curated pass|complete initial curated passes)\.',lambda _:completion,readme)
    inventory=' '.join(r['book']+' has '+format(r['units'],',')+' inventoried source units, of which '+format(r['count'],',')+' are completed.' for r in reports)
    readme=re.sub(r'Each active book receives[^\n]+','Each active book receives a complete inventory from its declared source edition before review. Pending books have no invented verse totals. '+inventory,readme)
    readme=re.sub(r'After updating the structured records[^\n]+','After updating structured records and progress, run `python scripts/render_books.py` to refresh all inventoried books and README counts, then `python scripts/validate.py --write-verification`. The existing `render_genesis.py` entry point runs the same multi-book renderer.',readme)
    marker='\nLatest saved review: '
    if marker in readme:readme=readme[:readme.index(marker)].rstrip()
    run=progress['runs'][-1]
    readme+=f'\n\nLatest saved review: {run["date"]}, **{run["new_completed_pairs"]} new pairs across {run["distinct_source_verses"]} source verses**. Hourly target: {run["hourly_target"]}; shortfall: {run.get("target_shortfall",max(0,500-run["new_completed_pairs"]))}. [Review record]({run["review_record"]}).\n'
    write(ROOT/'README.md',readme)
    print(json.dumps({'rendered_books':[{k:v for k,v in r.items() if k!='record'} for r in reports],'next':next_ref}))

if __name__=='__main__':main()
