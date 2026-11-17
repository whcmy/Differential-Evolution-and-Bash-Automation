"""Remove optional metadata without changing visible content."""
from pathlib import Path
from io import BytesIO
import zipfile
import xml.etree.ElementTree as E
from PIL import Image
from PIL.PngImagePlugin import PngInfo

AUTHOR = '殷明骏'
DC = 'http://purl.org/dc/elements/1.1/'
CP = 'http://schemas.openxmlformats.org/package/2006/metadata/core-properties'

def clean_png_bytes(data):
    im = Image.open(BytesIO(data))
    if set(im.info) <= {'Author', 'dpi'} and im.info.get('Author') == AUTHOR:
        return data
    info = PngInfo()
    info.add_text('Author', AUTHOR)
    out = BytesIO()
    args = {'pnginfo': info}
    if 'dpi' in im.info:
        args['dpi'] = im.info['dpi']
    im.save(out, format='PNG', **args)
    return out.getvalue()

def clean_docx(path):
    path = Path(path)
    temp = path.with_suffix('.metadata.docx')
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as out:
        assert not any('/comments' in n for n in source.namelist()), 'Remove Word comments before packaging'
        for name in source.namelist():
            data = source.read(name)
            if name == 'docProps/core.xml':
                root = E.fromstring(data)
                keep = {'{'+DC+'}title', '{'+DC+'}creator', '{'+CP+'}lastModifiedBy'}
                for child in list(root):
                    if child.tag not in keep:
                        root.remove(child)
                for tag in ['{'+DC+'}creator', '{'+CP+'}lastModifiedBy']:
                    node = root.find(tag)
                    if node is None:
                        node = E.SubElement(root, tag)
                    node.text = AUTHOR
                data = E.tostring(root, encoding='utf-8', xml_declaration=True)
            elif name == 'docProps/app.xml':
                root = E.fromstring(data)
                for child in list(root):
                    root.remove(child)
                data = E.tostring(root, encoding='utf-8', xml_declaration=True)
            elif name.startswith('word/media/') and name.lower().endswith('.png'):
                data = clean_png_bytes(data)
            out.writestr(name, data)
    temp.replace(path)

def clean_pdf(path):
    import fitz
    path = Path(path)
    with fitz.open(path) as doc:
        title = doc.metadata.get('title', '')
        doc.set_metadata({'title': title, 'author': AUTHOR, 'creator': '', 'producer': '',
                          'subject': '', 'keywords': '', 'creationDate': '', 'modDate': ''})
        doc.del_xml_metadata()
        for page in doc:
            for annot in list(page.annots() or []):
                page.delete_annot(annot)
        temp = path.with_suffix('.metadata.pdf')
        doc.save(temp, garbage=3, deflate=True)
    temp.replace(path)

def main():
    root = Path(__file__).resolve().parent
    # Published source articles and protocol PDFs retain their original provenance.
    for path in (root / 'output/figures').glob('*.pdf'):
        clean_pdf(path)
    for path in (root / 'output/figures').glob('*.png'):
        path.write_bytes(clean_png_bytes(path.read_bytes()))
    for path in (root / 'source/template').glob('*.docx'):
        clean_docx(path)
    for path in [root / 'output/Baseline_Study.docx']:
        if path.exists():
            clean_docx(path)
    for path in [root / 'output/pdf/Baseline_Study.pdf', root / 'output/pdf/report.pdf']:
        if path.exists():
            clean_pdf(path)
    print('Cleared optional metadata from authored report assets and template copies')

if __name__ == '__main__':
    main()
