# Differential Evolution and Reproducible Optimization

差分进化算法改进与可复现实验研究

围绕差分进化算法的性能改进与实验可复现性开展研究。在团队完成 DSPDE、DLS-DE 与 PEMS-DE 复现的基础上，负责 PEMS-DE 复现、跨算法对比、策略消融与 DC-DE 改进方法的实现和验证。构建基于成功反馈的指数／二项交叉自适应混合机制，在 CEC2014 的 30 个十维函数上完成 4,800 次独立确认运行，DC-DE 在六种完整算法中的平均排名为 2.367；经 Holm 校正的配对检验，相对基础 DE 在 14 个函数上显著改善、1 个函数上显著下降。同时完成参考评价器核验，并搭建 Bash 与 cron 驱动的实验流程，支持参数扫描、结构化日志、保存解的独立重算与结果追溯；三次定时执行产生并核验 270 条结果。

| 研究内容 | 报告 | 代码与记录 |
| --- | --- | --- |
| DE 基线、评价器一致性与文献对照 | [PDF](研究报告/Differential%20Evolution%20Baseline%20and%20Evaluator%20Validation.pdf) · [Word](研究报告/Differential%20Evolution%20Baseline%20and%20Evaluator%20Validation.docx) | [basic_de](脚本/BasicDE/) |
| 自适应差分进化复现、策略消融与 DC-DE 验证 | [PDF](研究报告/Adaptive%20Differential%20Evolution%20and%20DC-DE%20Validation.pdf) · [Word](研究报告/Adaptive%20Differential%20Evolution%20and%20DC-DE%20Validation.docx) | [adaptive_de](脚本/AdaptiveDE/) |
| 优化实验自动化、参数扫描与独立核验 | [PDF](研究报告/Reproducible%20Optimization%20Experiment%20Automation.pdf) · [Word](研究报告/Reproducible%20Optimization%20Experiment%20Automation.docx) | [automation](脚本/Automation/) |

实验运行入口与依赖见[运行说明](脚本/运行说明.md)。`开发脚本/` 保留算法开发、分析、绘图、文档构建和打包脚本。基线验证与自适应算法使用不同 NumPy 版本，分别配置环境。保存的历史实现、消融结果和执行记录用于复核研究过程。
