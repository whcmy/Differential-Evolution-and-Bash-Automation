# AdaptiveDE 脚本与实验记录

建议环境：Python 3.12、NumPy 2.3.5、SciPy 1.16.3、opfunu 1.0.4；完整版本清单见 `requirements.lock.txt`。opfunu在Python 3.12下安装需要允许其Python版本声明限制，并保留 setuptools 80.9.0。

`code/` 包含基础DE及三篇论文算法、原PGE-DE；最终DC-DE在 `improvement_v2/dls_combined.py` 中，运行名为 `DUAL`。最终确认的4800条记录在 `improvement_v2/results/confirmation/`，统计和检验结果在 `improvement_v2/analysis/`。

在本目录中运行：

```bash
python code/run_adaptive_de.py --help
python improvement_v2/run_confirmation.py --help
python improvement_v2/run_confirmation.py --algorithms DE DSPDE DLSDE PEMSDE TEAM DUAL DUAL_no_phase DUAL_no_learning --runs 20 --seed 20261118 --workers 8 --output results_new
python improvement/verify_records.py improvement_v2/results/confirmation --expected 4800
```

`results/common_benchmark/` 是原统一条件实验，`results/pems_native_reference/` 是PEMS-DE原条件实验；`legacy/` 保留DSPDE和DLS-DE的原条件与消融实验。`source/` 与 `vendor/` 保留参考评价器、论文数值对照和所需基准数据。新实验使用新目录。
