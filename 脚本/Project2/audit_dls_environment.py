"""Reevaluate original DLS-DE solutions without changing original records."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
from pathlib import Path
import json
import numpy as np
from opfunu.cec_based import cec2014

root = Path(__file__).resolve().parent
delivery = root.parent/'project2_dlsde_delivery'
checks = []
problems = {}
for directory in ('results', 'results_ablation'):
    for path in sorted((delivery/directory).glob('*/*.json')):
        row = json.loads(path.read_text(encoding='utf-8-sig'))
        fid = row['function']
        if fid not in problems:
            problems[fid] = getattr(cec2014, f'F{fid}2014')(ndim=10)
        value = float(problems[fid].evaluate(np.array(row['best_x'])))
        saved = row['best_fitness']
        checks.append(dict(path=str(path.relative_to(delivery)), saved=saved, recomputed=value,
                           difference=value-saved, passed=bool(np.isclose(value, saved, rtol=1e-10, atol=1e-8))))
out = dict(author='殷明骏', student_id='202483890029', numpy=np.__version__, count=len(checks),
           passed=sum(r['passed'] for r in checks), failures=[r for r in checks if not r['passed']],
           max_abs_difference=max(abs(r['difference']) for r in checks))
(root/'output/dls_environment_check.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(out, ensure_ascii=False, indent=2))
