"""Render every report page and contact sheet for visual QA; 殷明骏."""
from pathlib import Path
import json
import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent


def main():
    doc = fitz.open(ROOT/'output/pdf/Project2_Report.pdf')
    qa = ROOT/'output/qa'
    pages = qa/'pages'
    pages.mkdir(parents=True, exist_ok=True)
    evidence = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
        target = pages/f'page-{i+1:03d}.png'
        pix.save(target)
        spans = [s for block in page.get_text('dict')['blocks'] if 'lines' in block
                 for line in block['lines'] for s in line['spans']]
        clipped = [s['text'] for s in spans if fitz.Rect(s['bbox']).x0 < -1
                   or fitz.Rect(s['bbox']).y0 < -1 or fitz.Rect(s['bbox']).x1 > page.rect.width+1
                   or fitz.Rect(s['bbox']).y1 > page.rect.height+1]
        evidence.append(dict(page=i+1, width=page.rect.width, height=page.rect.height,
                             text_characters=len(page.get_text()), spans=len(spans),
                             clipped_text=clipped, rendered=str(target.relative_to(ROOT))))
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 16)
    for start in range(0, len(doc), 12):
        sheet = Image.new('RGB', (1280, 1500), '#DDE3E8')
        draw = ImageDraw.Draw(sheet)
        for j, i in enumerate(range(start, min(start+12, len(doc)))):
            im = Image.open(pages/f'page-{i+1:03d}.png').convert('RGB')
            im.thumbnail((300, 455))
            x, y = 10+(j % 4)*320, 30+(j//4)*500
            sheet.paste(im, (x+(300-im.width)//2, y))
            draw.text((x+10, y-23), f'Page {i+1}', fill='#253746', font=font)
        sheet.save(qa/f'contact-{start//12+1:02d}.png')
    result = dict(author='殷明骏', student_id='202483890029', page_count=len(doc),
                  metadata=doc.metadata, pages=evidence,
                  geometric_clipping_passed=not any(r['clipped_text'] for r in evidence),
                  visual_review='PENDING: assistant must inspect all page contact sheets and representative full-size pages')
    (qa/'render_audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'pages'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
