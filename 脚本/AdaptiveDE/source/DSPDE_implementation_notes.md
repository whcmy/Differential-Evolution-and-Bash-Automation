# Historical DSPDE source notes

The notes below describe the earlier standalone DSPDE delivery and its local evaluator experiments. They do not define the final AdaptiveDE common comparison. The final common track uses unmodified opfunu 1.0.4, CEC2014 10D, fixed NP 100 and 100,000 FEs; its executed configuration is `results/common_benchmark/manifest.json`. Native/source-ablation records and C++ evaluator controls are separate tracks, described in the final README and the main-body reproduction, evaluator and component sections. Paths and run totals below belong to the historical delivery.

# 2026-10-29补充：本目录使用CEC2014本地校正版

本目录的算法核心、参数及四项消融与原交付相同；仅CEC2014评价实现更换为经官方C参考逐点验证的本地校正版。修正范围为F13、F17-F30；其余F1-F12、F14-F16仍直接调用原opfunu类。不能把本目录称为未修改opfunu。原实验保留于原交付目录。CEC2022原opfunu实验保留，本目录另有480次发布C参考代码的补充实验（opfunu提供元数据，目标值来自C内核），见run_official2022.py及相关manifest。两批结果分开报告。

13个结构差异函数为F17-F27、F29-F30；F13/F28另外处理了已记录的浮点敏感位置。新增1800次运行，逐字节复用1800次未修改函数的历史记录；来源写入manifest。所有作者参数与公式歧义仍然存在，见下方沿用的方法说明。

---

# DSPDE 实现约定与复现边界

## 来源与状态

原文：Qu C, Yuan J, Zhang L, Zhang X, Huang Z. DSPDE: A synergistic integration of dynamic stratification and probabilistic escape for enhanced differential evolution optimization. Swarm and Evolutionary Computation 104 (2026), 102380. DOI: 10.1016/j.swevo.2026.102380。

已读取本地25页PDF，并对结构执行preflight（PASS，仅结构）。出版商页面的检索结果可确认文献信息；直接访问页面返回403。定向检索未定位到该2026版DSPDE的公开作者代码或补充附件。论文声明数据可向作者索取。本次未联系作者，也未取得未公开参数。

交付代码是**依据论文重建的参考实现**，不是已经证明逐项等同于作者程序的精确复现。不以调整参数逼近论文表格为验收依据。

## 逐项映射

| 项目 | 来源 | 本实现 |
| --- | --- | --- |
| 总种群规模 | 第4.5.1节 | 固定NP=50 |
| 评价预算 | 第4.5.1节 | 75000次，含初始化，所有版本一致 |
| 重复次数 | 第4.1节、研究要求 | 每函数20次 |
| 复现测试集 | 第4节 | CEC2022的12函数 |
| 测试维度 | 表7/第4.5节未明确给出 | 选择10D，不能保证与表7维度相同 |
| 作业策略实验 | Test condition | CEC2014的30函数、10D |
| 分层 | 第3.2节 | Ng=max(6,round(N*0.618/3))；最好/最差Ng，余者普通组 |
| 动态含义 | 第3.2节、固定NP | 每代按当前适应度重新分配角色；固定NP下Ng数量不变 |
| GMM统计量 | 公式6-7 | 每代一次；样本协方差ddof=1，加1e-6 I |
| 混合权重 | 第3.3节 | 精英0.7、全局0.3 |
| 逃逸触发 | 第6页公式8与正文不一致 | 依据正文采用“当前最差Ng且密度小于tau”；公式8实际重复了精英更新式 |
| 阈值与步长 | 公式11、14 | tau=.2(1-.9q)，step=.1(1-.9q) |
| 进度q | 论文为t/MaxIt；作业要求按评价数停止 | q=当前更新代/ceil((MaxFEs-NP)/NP)，包含最后不足一代 |
| 逃逸算子 | Algorithm1、公式12-16 | 0.7概率反密度梯度加噪声，0.3概率交叉均值镜像采样；小梯度时仅加噪声 |
| 梯度数值 | 公式10、13、Algorithm1 | 在对数域计算密度和梯度缩放，保留绝对密度及epsilon门限，不把grad(log p)直接冒充grad(p) |
| 梯度门限epsilon | Algorithm1给出符号epsilon，未单独规定数值 | 选1e-6；代码与协方差正则项共用该数值，但不将二者解释为同一概念 |
| 精英候选 | 公式17-18 | 随机个体坐标加Linnik变量，仅在rand<eta的坐标替换 |
| Linnik参数 | 原文未给出数值 | 明确选alpha=1.0、v=0.5；这是实现约定，不是论文默认值 |
| Linnik随机池 | 论文提到预生成池，未给池大小/重采样细节 | 直接生成随机变量，不另造随机池规格 |
| Linnik实数幂 | 公式17对一般非整数alpha可能遇到负底数 | 代码显式采用带符号实数幂；默认alpha=1时与原式代数一致，不需要该延拓 |
| 维度选择 | 公式18用eta，正文又举1/D示例 | 主实现按公式18，不额外加入1/D门限或强制交叉 |
| 普通组 | 公式19-20 | best+lambda*(best-xi)+r*(xr1-xi)；同一个体的r为标量；非自身同伴均匀抽取 |
| 知识获取率 | 公式21-22 | 一基排名；round(U1*phi+I[U2<=phi])/2；MATLAB式正数舍入；得到0、0.5、1 |
| 边界 | Algorithm2未指定具体规则 | clip到[-100,100]，所有版本一致 |
| 更新 | Algorithm2未明确供体能否代内更新 | 采用整代旧种群生成候选，整代严格贪婪选择 |
| 无变化候选 | 伪代码仍调用评价 | 仍计一次实际评价，记录noop数量，不偷偷获得额外搜索预算 |

公式14在q=1时step=0.01，公式20在q=1时lambda=0.1；实现保留公式值，不按正文“接近零”的表述改成0。

## 消融定义

- DSPDE：上述完整参考实现。
- without_escape：仅将劣势组的模型逃逸替换为Algorithm2已有的均匀随机重置；其余不变。
- without_linnik：仅将精英组候选替换为DE/rand/1/bin（F=.5, CR=.9）；其余不变。
- without_social：仅将普通组候选替换为相同DE/rand/1/bin；其余不变。
- frozen_roles：仅把角色成员固定为初始化时的分组；当前适应度排名、eta、模型统计仍随代更新。
- DE：基础DE/rand/1/bin，F=.5、CR=.9，与各版本使用相同NP、预算和边界。

这些消融是本次作业明确定义的干预。frozen_roles不是未经说明地等同于论文表8的StaticGroup，三个without版本也不是声称复现了论文表3的单算子版本。

## 本篇在AdaptiveDE中的范围

完成DSPDE这一篇的代码、原测试集实验与表7数值对照、研究测试集消融、基础DE比较、排名和收敛曲线。另两篇论文、跨三篇选择策略和团队新算法不属于“DSPDE这一篇”的交付，需小组后续整合。

即使所有实验成功运行，缺失的作者参数、维度和代码仍限制精确复现判定。最终报告会根据实测表格说明差异，不自动给出“接近原文”或“优于基础DE”的结论。

论文第4.5.2.1节把F9的2529.2844描述为理论最优，而当前opfunu CEC2022 F9声明的最优值为2300。本交付使用库提供的2300计算误差，保留论文原始目标值2529.2844用于对照，不沿用该“理论最优”表述。
