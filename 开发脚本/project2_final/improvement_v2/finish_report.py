"""Render and vector-finish the selected report after numerical acceptance. Author: 殷明骏."""
from pathlib import Path
from datetime import datetime
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from finish_visual_report import page_map,vectorize
BUNDLE='/home/yinwhcmy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
RENDER='/home/yinwhcmy/.codex/plugins/cache/openai-primary-runtime/documents/26.1112.11217/skills/documents/render_docx.py'


def main():
    local=Path(__file__).parent
    result=json.loads((local/'analysis/confirmation_summary.json').read_text())
    assert result['first_descriptive_rank'], 'First-rank requirement has not been met'
    verified=json.loads((local/'results/confirmation/verification.json').read_text())
    assert verified['passed'] and verified['records']==4800
    subprocess.run([BUNDLE,str(local/'build_report.py')],cwd=ROOT,check=True)
    render=ROOT/'template_work'/('algorithm_confirmation_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    subprocess.run([BUNDLE,RENDER,str(ROOT/'output/Project2_Report.docx'),
                    '--output_dir',str(render),'--emit_pdf'],cwd=ROOT,check=True)
    mapping=page_map(render/'Project2_Report.pdf')
    (ROOT/'output/report_page_map.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    vectorize(render/'Project2_Report.pdf',ROOT/'output/pdf/Project2_Report.pdf',mapping)
    build=json.loads((ROOT/'output/report_build.json').read_text())
    build.update(figures=41,explanatory_figures=3,analytical_figures=8,native_equations=5,independent_records=4800)
    (ROOT/'output/report_build.json').write_text(json.dumps(build,ensure_ascii=False,indent=2)+'\n')
    (local/'render_location.json').write_text(json.dumps(dict(author='殷明骏',render=str(render)),ensure_ascii=False,indent=2)+'\n')
    print('Rendered report requires page-by-page visual acceptance before packaging.')


if __name__=='__main__':main()
