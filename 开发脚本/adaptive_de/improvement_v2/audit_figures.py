"""Audit the exact figure set embedded in the revised report. Author: 殷明骏."""
from pathlib import Path
import hashlib
import json
import sys
import fitz
from lxml import etree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from audit_pdf_text import audit_pdf as font_audit
from audit_figure_collisions import audit_pdf as collision_audit,exit_code


def main():
    names=json.loads((ROOT/'output/report_figures.json').read_text())
    assert len(names)==16
    results=[]
    for name in names:
        path=ROOT/'output/figures'/f'{name}.pdf'
        font=font_audit(path.read_bytes(),minimum_pt=5)
        collision=collision_audit(path)
        alignment=json.loads(path.with_suffix('.alignment.json').read_text())
        assert font['auditable'] and not font['below_minimum_count'],(name,font)
        assert exit_code(collision)==0,(name,collision)
        assert alignment['verdict']=='PASS' or (alignment['verdict']=='NOT APPLICABLE' and len(alignment['layout']['panels'])==1),(name,alignment)
        with fitz.open(path) as doc:
            assert len(doc)==1 and doc.metadata['author']=='殷明骏'
            assert not any(doc.metadata.get(k) for k in ['creator','producer','subject','keywords'])
            assert not doc.get_xml_metadata()
        svg=etree.parse(str(path.with_suffix('.svg')))
        assert not svg.xpath('//comment()'),name
        creators=svg.findall('.//{http://purl.org/dc/elements/1.1/}creator')
        assert creators and all('殷明骏' in ''.join(x.itertext()) for x in creators),name
        path.with_suffix('.collision.json').write_text(json.dumps(collision,ensure_ascii=False,indent=2)+'\n')
        path.with_suffix('.font.json').write_text(json.dumps(font,ensure_ascii=False,indent=2)+'\n')
        results.append(dict(figure=name,pdf_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            font_code=0,collision_code=0,alignment=alignment['verdict'],minimum_font_pt=font['minimum_found_pt'],
                            collision_warnings=collision['summary']['warn'],metadata_passed=True))
    (ROOT/'output/confirmation_figure_audit.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
