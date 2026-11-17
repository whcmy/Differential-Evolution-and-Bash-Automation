# BasicDE 脚本与实验记录

运行环境：Python 3.11/3.12、NumPy 1.26.4、opfunu 1.0.4。建议为本实验单独建立环境。

基础实验入口为 `run_experiments.py`；`results/` 保留600次研究实验。`consistency/results_official/` 为600次参考评价器实验，`consistency/results_paper/` 为560次同算法论文对照。

```bash
python run_experiments.py --help
python run_experiments.py --workers 8 --output results_new
python summarize.py --results results_new --output output_new
```

补充验证入口为 `consistency/run_validation.py`，还需 JPype1、JDK 和 g++。Java源文件、编译类、基准数据与源代码许可均随脚本保留。新实验使用新目录，保留已有记录。
