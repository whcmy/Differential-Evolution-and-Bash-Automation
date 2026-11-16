"""Place all numerical evidence inside the main report. Author: 殷明骏."""
import re
from lxml import etree
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'

def visible(node):
    return ''.join(t.text or '' for t in node.iter(qn('w:t')))

def retitle(node,text):
    ts=list(node.iter(qn('w:t')))
    caption=re.match(r'^(?:Figure|Table) [A-Z]?\d+[a-z]?\.',text)
    if caption and len(ts)>1:
        ts[0].text=text[:caption.end()]
        ts[1].text=text[caption.end():]
        for t in ts[2:]:t.text=''
        return
    ts[0].text=text
    for t in ts[1:]:t.text=''

def integrate(report,titles,figures,text):
    body=report.doc._element.body;nodes=list(body)
    groups={};heading_nodes={}
    starts=[]
    for item in titles:
        n=next(n for n in nodes if any(b.get(qn('w:name'))==item['anchor'] for b in n.iter(qn('w:bookmarkStart'))))
        starts.append((nodes.index(n),item['title']));heading_nodes[item['title']]=n
    starts.sort()
    for k,(start,title) in enumerate(starts):
        end=starts[k+1][0] if k+1<len(starts) else len(nodes)-1
        groups[title]=nodes[start:end]
    old_titles={item['title']:item for item in titles}
    section_order=['1 Introduction','2 Methods','Appendix A Reproduction details']
    section_order+=['Appendix B1 DSPDE original condition results','Appendix B2 DLS-DE original condition results','Appendix B3 PEMS-DE original condition results']
    section_order+=['3 Benchmark fidelity','4 Component strategy evidence']
    for family in ['F DSPDE','G DLS-DE','D PEMS-DE']:
        section_order += [t for _,t in starts if t.startswith('Appendix '+family)]
    section_order+=['5 Comparative performance']
    for family in ['C Five','E PGE-DE','H Convergence']:
        section_order += [t for _,t in starts if t.startswith('Appendix '+family)]
    section_order+=['6 Mechanistic interpretation','7 Conclusions','References']
    assert set(section_order)==set(groups) and len(section_order)==len(groups)
    rename={'Appendix A Reproduction details':'2.4 Reproduction and validation details',
            'Appendix B1 DSPDE original condition results':'3 Original-condition reproduction',
            'Appendix B2 DLS-DE original condition results':'3.2 DLS-DE original-condition reproduction',
            'Appendix B3 PEMS-DE original condition results':'3.3 PEMS-DE original-condition reproduction',
            '3 Benchmark fidelity':'4 Benchmark fidelity','4 Component strategy evidence':'5 Component strategy evidence',
            '5 Comparative performance':'6 Comparative performance','6 Mechanistic interpretation':'7 Mechanistic interpretation',
            '7 Conclusions':'8 Conclusions'}
    prefix={'C Five algorithm statistics':'6.2 Five-algorithm statistics',
            'D PEMS-DE ablations':'5.4 PEMS-DE component statistics','E PGE-DE ablations':'6.3 PGE-DE component statistics',
            'F DSPDE ablations':'5.2 DSPDE component statistics','G DLS-DE native ablations':'5.3 DLS-DE native component statistics',
            'H Convergence curves':'6.4 Convergence curves'}
    for old in section_order:
        if old not in rename and old.startswith('Appendix '):
            for stem,new in prefix.items():
                if old.startswith('Appendix '+stem):rename[old]=old.replace('Appendix '+stem,new)
        retitle(heading_nodes[old],rename.get(old,old))
    dsp_heading=OxmlElement('w:p');ppr=OxmlElement('w:pPr');style=OxmlElement('w:pStyle')
    style.set(qn('w:val'),report.doc.styles['Paper Heading 2'].style_id);ppr.append(style);dsp_heading.append(ppr)
    run=OxmlElement('w:r');value=OxmlElement('w:t');value.text='3.1 DSPDE original-condition reproduction';run.append(value);dsp_heading.append(run)
    groups['Appendix B1 DSPDE original condition results'].insert(1,dsp_heading)
    # Continue the short guide-definition block into validation details.
    validation=heading_nodes['Appendix A Reproduction details']
    page_break=validation.find(qn('w:pPr')).find(qn('w:pageBreakBefore'))
    if page_break is not None:page_break.set(qn('w:val'),'0')
    conclusion_break=heading_nodes['7 Conclusions'].find(qn('w:pPr')).find(qn('w:pageBreakBefore'))
    if conclusion_break is not None:conclusion_break.set(qn('w:val'),'1')
    for node in groups['Appendix A Reproduction details'][1:]:
        if node.tag!=qn('w:p'):continue
        ppr=node.find(qn('w:pPr'))
        if ppr is None:ppr=OxmlElement('w:pPr');node.insert(0,ppr)
        spacing=ppr.find(qn('w:spacing'))
        if spacing is None:spacing=OxmlElement('w:spacing');ppr.append(spacing)
        spacing.set(qn('w:line'),'276');spacing.set(qn('w:lineRule'),'auto');spacing.set(qn('w:after'),'80')
    front=nodes[:starts[0][0]]
    for n in nodes[starts[0][0]:]:
        if n.tag!=qn('w:sectPr'):body.remove(n)
    sect=body.find(qn('w:sectPr'))
    for name in section_order:
        for n in groups[name]:sect.addprevious(n)
    titles[:]=[dict(old_titles[name],title=rename.get(name,name)) for name in section_order]
    replacements={'4.1 Candidate strategies and controls':'5.1 Candidate strategies and controls',
                  '5.1 Seed distributions and heterogeneity':'6.1 Seed distributions and heterogeneity',
                  'Appendix A':'Section 2.4','Appendix B':'Section 3','Appendix H':'Section 6.4',
                  'Appendices retain':'The main text retains','appendices retain':'the main text retains'}
    # Replace cross-references without touching native equations or fields.
    for n in body:
        if n.tag!=qn('w:p'):continue
        s=visible(n)
        if not s:continue
        changed=s
        for a,b in replacements.items():changed=changed.replace(a,b)
        if changed!=s:retitle(n,changed)
    desired=[('1 Introduction','1 Introduction'),('2 Methods','2 Methods'),
             ('3 Original-condition reproduction','3 Original-condition reproduction'),
             ('4 Benchmark fidelity','4 Benchmark fidelity'),('5 Component strategy evidence','5 Component strategy evidence'),
             ('5.2 DSPDE statistics',next(t['title'] for t in titles if t['title'].startswith('5.2 '))),
             ('5.3 DLS-DE statistics',next(t['title'] for t in titles if t['title'].startswith('5.3 '))),
             ('5.4 PEMS-DE statistics',next(t['title'] for t in titles if t['title'].startswith('5.4 '))),
             ('6 Comparative performance','6 Comparative performance'),
             ('6.2 Five-algorithm statistics',next(t['title'] for t in titles if t['title'].startswith('6.2 '))),
             ('6.3 PGE-DE statistics',next(t['title'] for t in titles if t['title'].startswith('6.3 '))),
             ('6.4 All 30 convergence curves',next(t['title'] for t in titles if t['title'].startswith('6.4 '))),
             ('7 Mechanistic interpretation','7 Mechanistic interpretation'),('8 Conclusions','8 Conclusions'),
             ('References','References')]
    assert len(report.contents)>=len(desired)
    for (p,_,_),(label,target) in zip(report.contents,desired):
        retitle(p._p,label)
    for p,_,_ in report.contents[len(desired):]:body.remove(p._p)
    report.contents[:]=[(report.contents[i][0],label,target) for i,(label,target) in enumerate(desired)]
    # Diagram-to-file mapping survives moving Word paragraphs.
    figures[:]=[name for node,name in sorted(report.figure_nodes,key=lambda pair:list(body).index(pair[0]))]
    figure_number=0;table_number=0;old_to_new={}
    for n in body:
        s=visible(n)
        m=re.match(r'^(Figure|Table) ([A-Z]?\d+[a-z]?)\.',s)
        if not m:continue
        if m[1]=='Figure':figure_number+=1;number=figure_number
        else:table_number+=1;number=table_number
        old_to_new[m[0][:-1]]=f'{m[1]} {number}'
        retitle(n,re.sub(r'^(Figure|Table) [A-Z]?\d+[a-z]?\.',f'{m[1]} {number}.',s))
    for n in body:
        if n.tag!=qn('w:p'):continue
        s=visible(n)
        if re.match(r'^(Figure|Table) \d+\.',s):continue
        # Longest keys first so Table 5 cannot consume Table 5a.
        pattern=r'\b(?:'+ '|'.join(re.escape(k) for k in sorted(old_to_new,key=len,reverse=True))+r')(?![\w])'
        changed=re.sub(pattern,lambda m:old_to_new[m[0]],s)
        if changed!=s:retitle(n,changed)
    # Recreate Markdown from the final main-body order.
    text[:]=['# NUIST Experiment Report']
    fig_index=0
    for n in body:
        if n.tag==qn('w:tbl'):
            rows=[[''.join(t.text or '' for t in c.iter(qn('w:t'))) for c in row.findall(qn('w:tc'))] for row in n.findall(qn('w:tr'))]
            if rows:
                text.append('| '+' | '.join(rows[0])+' |');text.append('| '+' | '.join('---' for _ in rows[0])+' |')
                text.extend('| '+' | '.join(row)+' |' for row in rows[1:])
        elif n.tag==qn('w:p'):
            if list(n.iter('{http://schemas.openxmlformats.org/drawingml/2006/main}blip')):
                text.append('![Figure](figures/'+figures[fig_index]+'.png)');fig_index+=1
            s=visible(n)
            if s:text.append(s)
            if list(n.iter('{http://schemas.openxmlformats.org/officeDocument/2006/math}oMath')):
                text.append(''.join(n.itertext()))
    assert fig_index==len(figures)
    assert not any('Appendix' in visible(n) or 'appendices' in visible(n).lower() for n in body)
