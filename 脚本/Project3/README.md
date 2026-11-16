# Project3 最终DC-DE自动化脚本

本目录使用Report2最终DC-DE，`code/dls_combined.py` 与Report2算法文件一致。依赖版本见 `requirements.lock.txt`。

先激活兼容的Python环境，然后在本目录执行：

```bash
./run_experiments.sh --help
./run_experiments.sh --output output/new_manual_batch --seed 2026111604
```

入口默认使用当前环境的python3，也可用 `PROJECT3_PYTHON=/绝对路径/python` 指定解释器。`original_run_experiments.sh`、算法源代码和已保存实验记录保持原样。一次完整运行覆盖三个种群规模，每种规模测试30个函数，需100000次实际函数评价/函数。

`cron/` 保留小时调度配置、日志和三次成功回执；`output/cron_*/` 保留270条实验记录及日志、汇总、验证结果；`results_summary.json` 和 `summary_report.txt` 为整体汇总。三次启动时间为2026-11-16的20:20:01、21:20:02、22:20:01。

`evidence/` 保留调度与操作证据，`evidence/report_evidence/screenshots/` 包含报告中的结果截图。调度配置中的绝对路径对应原执行环境；在其他机器重新配置时，将其替换为本目录实际路径。手动运行与新调度结果使用新目录。
