"""Build, render and vector-finish the Project3 report. Author: 殷明骏."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
import fitz
import numpy as np
from PIL import Image
from clean_metadata import clean_pdf
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'output'
BUNDLE=Path('/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies')
PYTHON=BUNDLE/'python/bin/python3'
RENDER=Path('/home/yinwhcmy/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents/render_docx.py')
def norm(s):return ''.join(s.split())
def vectorize(source,render):
    names=json.loads((OUT/'report_figures.json').read_text());assets={n:Image.open(OUT/'figures'/f'{n}.png').convert('RGB') for n in names}
    doc=fitz.open(source);replaced=[];seen=set()
    for i,page in enumerate(doc):
        for info in page.get_image_info(xrefs=True):
            xref=info['xref']
            if not xref or xref in seen:continue
            seen.add(xref)
            for name,expected in assets.items():
                if abs((expected.width/expected.height)/(info['width']/info['height'])-1)>.003:continue
                pix=fitz.Pixmap(doc,xref)
                if pix.alpha:pix=fitz.Pixmap(pix,0)
                a=np.asarray(expected.resize((info['width'],info['height']),Image.Resampling.LANCZOS),dtype=float)
                b=np.frombuffer(pix.samples,dtype=np.uint8).reshape(info['height'],info['width'],3)
                mae=float(np.abs(a-b).mean())
                if mae>=5:continue
                box=fitz.Rect(info['bbox']);page.delete_image(xref)
                with fitz.open(OUT/'figures'/f'{name}.pdf') as asset:page.show_pdf_page(box,asset,0,keep_proportion=False)
                replaced.append(dict(page=i+1,figure=name,raster_agreement_mae=mae));break
    assert len(replaced)==len(names)==8,replaced
    sections=json.loads((OUT/'report_sections.json').read_text());toc=[];mapping={}
    for s in sections:
        pages=[i+1 for i,p in enumerate(doc) if i>=1 and norm(s['title']) in norm(p.get_text())]
        assert pages,s['title'];mapping[s['title']]=pages[0];toc.append([s['level'],s['title'],pages[0]])
    doc.set_toc(toc);audit=[]
    for i,p in enumerate(doc):
        spans=[s for b in p.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
        clipped=[s['text'] for s in spans if fitz.Rect(s['bbox']).x0<-.5 or fitz.Rect(s['bbox']).y0<-.5 or fitz.Rect(s['bbox']).x1>p.rect.width+.5 or fitz.Rect(s['bbox']).y1>p.rect.height+.5]
        assert not clipped,(i+1,clipped);assert len(p.get_text())>80,(i+1,'Blank page')
        audit.append(dict(page=i+1,text_characters=len(p.get_text()),clipped=[]))
    target=OUT/'pdf/Project3_Report.pdf';doc.set_metadata(dict(title='Project 3 Bash Automation and Experiment Analysis',author='殷明骏'))
    doc.save(target,garbage=3,deflate=True);doc.close();clean_pdf(target)
    (OUT/'report_page_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    (OUT/'render_audit.json').write_text(json.dumps(dict(author='殷明骏',draft=False,render_directory=str(Path(render).relative_to(ROOT)),pages=audit,outline=toc,vector_figures=replaced,geometric_clipping_passed=True,visual_review='PENDING: inspect all final Word/PDF pages'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(pages=len(audit),vector_sheets=len(replaced))))
def main():
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--from-render',type=Path);args=a.parse_args()
    if args.from_render:render=args.from_render
    else:
        subprocess.run([str(PYTHON),str(ROOT/'build_report.py')],check=True)
        render=ROOT/'template_work'/('paper_rebuild_'+datetime.now().strftime('%H%M%S'))
        subprocess.run([str(PYTHON),str(RENDER),str(OUT/'Project3_Report.docx'),'--output_dir',str(render),'--emit_pdf'],check=True)
    vectorize(render/'Project3_Report.pdf',render.resolve())
if __name__=='__main__':main()
