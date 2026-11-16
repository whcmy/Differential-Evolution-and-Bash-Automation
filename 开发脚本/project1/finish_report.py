"""Build and vector-finish the matching Word/PDF. Author: 殷明骏."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess
import sys
import numpy as np
import fitz
from PIL import Image

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
BUNDLE='/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
RENDER='/home/yinwhcmy/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents/render_docx.py'

def norm(s):return ''.join(s.split())

def page_map(pdf):
    doc=fitz.open(pdf);sections=json.loads((OUT/'report_sections.json').read_text());mapping={}
    for section in sections:
        matches=[i+1 for i,p in enumerate(doc) if i>=1 and norm(section['title']) in norm(p.get_text())]
        if not matches:raise ValueError('Heading not found '+section['title'])
        mapping[section['title']]=matches[0]
    return mapping

def vectorize(source,destination,mapping):
    figures=json.loads((OUT/'report_figures.json').read_text())
    digest={}
    for name in figures:
        im=Image.open(OUT/'figures'/f'{name}.png').convert('RGB')
        digest[hashlib.sha256(im.tobytes()).hexdigest()]=name
    doc=fitz.open(source);replaced=[]
    image_entries=[(i,info) for i,p in enumerate(doc) for info in p.get_image_info(xrefs=True) if info['width']>1000 and info['height']>500]
    assert len(image_entries)==len(figures),(len(image_entries),len(figures))
    sequence={(i,info['xref']):name for (i,info),name in zip(image_entries,figures)}
    for i,page in enumerate(doc):
        entries=page.get_image_info(xrefs=True)
        for info in entries:
            xref=info['xref']
            if not xref:continue
            pix=fitz.Pixmap(doc,xref)
            if pix.alpha:pix=fitz.Pixmap(pix,0)
            key=hashlib.sha256(pix.samples).hexdigest()
            name=digest.get(key,sequence.get((i,xref)))
            if name is None:continue
            expected=Image.open(OUT/'figures'/f'{name}.png')
            # The office renderer may encode the same image lossily. Verify
            # dimensions and page order, then quantify its pixel agreement.
            assert abs((expected.width/expected.height)/(info['width']/info['height'])-1)<.003,(name,expected.size,info)
            a=np.asarray(expected.convert('RGB').resize((info['width'],info['height']),Image.Resampling.LANCZOS),dtype=float)
            b=np.frombuffer(pix.samples,dtype=np.uint8).reshape(info['height'],info['width'],3)
            mae=float(np.abs(a-b).mean())
            assert mae<5,(name,mae)
            rect=fitz.Rect(info['bbox'])
            page.delete_image(xref)
            with fitz.open(OUT/'figures'/f'{name}.pdf') as figure:
                page.show_pdf_page(rect,figure,0,keep_proportion=False)
            replaced.append(dict(page=i+1,figure=name,rectangle=list(rect),raster_agreement_mae=mae))
    assert len(replaced)==len(figures),(len(replaced),len(figures))
    sections=json.loads((OUT/'report_sections.json').read_text())
    doc.set_toc([[1,s['title'],mapping[s['title']]] for s in sections])
    doc.set_metadata(dict(title='Project 1 Basic Differential Evolution',author='殷明骏',
                          creator='',producer='',subject='',keywords='',creationDate='',modDate=''))
    doc.del_xml_metadata()
    for page in doc:
        for annot in list(page.annots() or []):page.delete_annot(annot)
    temporary=Path(destination).with_suffix('.building.pdf')
    doc.save(temporary,garbage=3,deflate=True)
    temporary.replace(destination)
    audit=dict(author='殷明骏',student_id='202483890029',pages=len(doc),vector_figures=replaced,
               source='Template-based Word render with revised contribution block; figure rasters replaced at identical bounds by original vector PDF exports',
               page_map=mapping,source_render=str(Path(source).relative_to(ROOT)))
    (OUT/'visual_revision_build.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    (OUT/'report_build.json').write_text(json.dumps(dict(author='殷明骏',student_id='202483890029',total_pages=len(doc),
        analytical_figures=6,process_figures=2,convergence_figures=58,convergence_sheets=4,vector_sheets=len(replaced),source=audit['source']),ensure_ascii=False,indent=2))
    print(json.dumps(dict(pages=len(doc),vector_figures=len(replaced)),indent=2))

def main():
    current=None
    stamp=datetime.now().strftime('%H%M%S')
    for iteration in [1,2]:
        render=ROOT/'report_work'/f'visual_revision_{stamp}_{iteration:02d}'
        cmd=[BUNDLE,str(ROOT/'build_report.py')]
        if current:cmd.append(str(current))
        subprocess.run(cmd,check=True,stdout=(ROOT/'report_work'/f'visual_build_{iteration}.log').open('w'))
        subprocess.run([BUNDLE,RENDER,str(OUT/'Project1_Report.docx'),'--output_dir',str(render),'--emit_pdf'],check=True)
        mapping=page_map(render/'Project1_Report.pdf')
        if current:
            assert mapping==json.loads(current.read_text()),'Pagination changed after TOC update'
        current=OUT/'report_page_map.json';current.write_text(json.dumps(mapping,indent=2)+'\n')
    vectorize(render/'Project1_Report.pdf',OUT/'pdf/Project1_Report.pdf',mapping)

if __name__=='__main__':main()
