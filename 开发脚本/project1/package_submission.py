"""Synchronize the final submission archives. Author: 殷明骏."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
DEST = ROOT.parent / 'Project1_殷明骏_202483890029_Final.zip'

def main():
    shutil.copy2(ROOT/'output/pdf/Project1_Report.pdf', ROOT/'output/pdf/report.pdf')
    shutil.copy2(ROOT/'output/Project1_Report.md', ROOT/'output/report.md')
    collected=ROOT.parent/'Project123_报告与代码/project1'
    if collected.is_dir():
        shutil.copy2(ROOT/'output/pdf/Project1_Report.pdf', collected/'Project1_Report.pdf')
        shutil.copy2(ROOT/'output/Project1_Report.docx', collected/'Project1_Report.docx')
        scripts=collected/'脚本';scripts.mkdir(exist_ok=True)
        for name in ['de.py','run_experiments.py','summarize.py','verify_results.py','test_project1.py','requirements.txt']:
            shutil.copy2(ROOT/name,scripts/name)
        for name in ['consistency','results','reference']:
            shutil.copytree(ROOT/name,scripts/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        (scripts/'README.md').write_text('''# Project1 脚本与代码

作者、最后修改者：殷明骏。

保留原 600 次课程实验，并新增 600 次原源码评价器重跑及 560 次同算法论文对照。完整报告为上级目录的 Word/PDF；绘图、报告生成及全部复核材料在 Final.zip 中。

原课程代码为 de.py、run_experiments.py；results/ 保留原始结果。新增实验与检查位于 consistency/，其 PROTOCOL.md 记录参数、算法细节和对照范围。论文对照使用专用非旋转测试集的全部 28 个适用函数；F21 差异保留。

安装 requirements.txt 后运行原实验；新增检查还需要 JPype1、JDK 和 g++。所有复算应在本目录进行，独立重跑请使用副本。consistency/run_validation.py 会跳过已有记录；consistency/analyze_validation.py 复算全部对照、探针及保存解。原冻结代码与记录不变。
''',encoding='utf-8')
    excluded_dirs = {'report_work', 'revision_work', 'design_previews', '__pycache__', '.venv', '.git'}
    excluded_files = {'render_report.py', 'report_data.json', 'package_validation.json'}
    files = []
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(ROOT)
        if any(x in excluded_dirs for x in rel.parts) or rel.parts[:2] == ('output', 'qa') or p.name in excluded_files:
            continue
        files.append(p)
    temp = DEST.with_suffix('.building.zip')
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.comment = b''
        for p in files:
            z.write(p, 'project1/' + p.relative_to(ROOT).as_posix())
    temp.replace(DEST)
    with zipfile.ZipFile(DEST) as z:
        assert z.testzip() is None and z.comment == b''
        for p in files:
            n = 'project1/' + p.relative_to(ROOT).as_posix()
            assert hashlib.sha256(z.read(n)).digest() == hashlib.sha256(p.read_bytes()).digest()
            assert z.getinfo(n).comment == b''
    for name in ['Project1交付.zip', 'project1_submission.zip']:
        shutil.copy2(DEST, ROOT.parent/name)
    result = dict(author='殷明骏', student_id='202483890029', passed=True, files=len(files),
                  bytes=DEST.stat().st_size, sha256=hashlib.sha256(DEST.read_bytes()).hexdigest(),
                  all_member_hashes_match=True, crc_passed=True, archive_comments_empty=True,
                  synchronized_archives=[DEST.name,'Project1交付.zip','project1_submission.zip'])
    (ROOT/'output/package_validation.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
